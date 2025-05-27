#!/bin/bash

# Hyperliquid Data Scraper EC2デプロイメントスクリプト

set -e

echo "================================================"
echo "Hyperliquid Data Scraper EC2 Deployment Script"
echo "================================================"

# 設定変数
APP_NAME="hyperliquid-data-scraper"
APP_DIR="/opt/${APP_NAME}"
DOCKER_COMPOSE_FILE="docker-compose.yml"
BACKUP_DIR="/opt/backups"
LOG_FILE="/var/log/${APP_NAME}-deploy.log"

# ログ関数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# エラーハンドリング
error_exit() {
    log "ERROR: $1"
    exit 1
}

# 前提条件チェック
check_prerequisites() {
    log "前提条件をチェックしています..."
    
    # rootユーザーかどうかチェック
    if [ "$EUID" -ne 0 ]; then
        error_exit "このスクリプトはroot権限で実行してください"
    fi
    
    # OSチェック（Amazon Linux/Ubuntu）
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        log "OS: $PRETTY_NAME"
    else
        error_exit "サポートされていないOSです"
    fi
}

# Dockerのインストール
install_docker() {
    log "Dockerをインストールしています..."
    
    # 既存のDockerを確認
    if command -v docker &> /dev/null; then
        log "Dockerは既にインストールされています"
        docker --version
    else
        # Amazon Linux 2の場合
        if grep -q "Amazon Linux" /etc/os-release; then
            yum update -y
            yum install -y docker
            systemctl start docker
            systemctl enable docker
            usermod -a -G docker ec2-user
        # Ubuntuの場合
        elif grep -q "Ubuntu" /etc/os-release; then
            apt-get update
            apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
            echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
            apt-get update
            apt-get install -y docker-ce docker-ce-cli containerd.io
            systemctl start docker
            systemctl enable docker
            usermod -a -G docker ubuntu
        else
            error_exit "サポートされていないLinuxディストリビューションです"
        fi
        
        log "Dockerのインストールが完了しました"
    fi
}

# Docker Composeのインストール
install_docker_compose() {
    log "Docker Composeをインストールしています..."
    
    if command -v docker-compose &> /dev/null; then
        log "Docker Composeは既にインストールされています"
        docker-compose --version
    else
        # 最新版のDocker Composeをダウンロード
        DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
        curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
        
        log "Docker Composeのインストールが完了しました"
        docker-compose --version
    fi
}

# アプリケーションディレクトリの設定
setup_app_directory() {
    log "アプリケーションディレクトリを設定しています..."
    
    # バックアップディレクトリの作成
    mkdir -p "$BACKUP_DIR"
    
    # 既存のアプリケーションディレクトリをバックアップ
    if [ -d "$APP_DIR" ]; then
        BACKUP_NAME="${APP_NAME}-backup-$(date +%Y%m%d-%H%M%S)"
        log "既存のアプリケーションをバックアップしています: $BACKUP_NAME"
        cp -r "$APP_DIR" "$BACKUP_DIR/$BACKUP_NAME"
    fi
    
    # アプリケーションディレクトリの作成
    mkdir -p "$APP_DIR"
    cd "$APP_DIR"
    
    log "アプリケーションディレクトリ: $APP_DIR"
}

# systemdサービスの作成
create_systemd_service() {
    log "systemdサービスを作成しています..."
    
    cat > /etc/systemd/system/${APP_NAME}.service << EOF
[Unit]
Description=Hyperliquid Data Scraper
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${APP_DIR}
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable ${APP_NAME}.service
    
    log "systemdサービスが作成されました"
}

# ログローテーションの設定
setup_log_rotation() {
    log "ログローテーションを設定しています..."
    
    cat > /etc/logrotate.d/${APP_NAME} << EOF
${APP_DIR}/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 appuser appuser
    postrotate
        docker-compose -f ${APP_DIR}/${DOCKER_COMPOSE_FILE} restart
    endscript
}
EOF

    log "ログローテーションが設定されました"
}

# 監視スクリプトの作成
create_monitoring_script() {
    log "監視スクリプトを作成しています..."
    
    cat > /usr/local/bin/${APP_NAME}-monitor.sh << 'EOF'
#!/bin/bash

APP_NAME="hyperliquid-data-scraper"
APP_DIR="/opt/${APP_NAME}"
LOG_FILE="/var/log/${APP_NAME}-monitor.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# コンテナの状態チェック
check_container_health() {
    cd "$APP_DIR"
    
    # コンテナが実行中かチェック
    if ! docker-compose ps | grep -q "Up"; then
        log "WARNING: コンテナが停止しています。再起動を試みます..."
        docker-compose up -d
        sleep 30
    fi
    
    # ヘルスチェック
    if ! docker-compose exec -T hyperliquid-scraper python healthcheck.py > /dev/null 2>&1; then
        log "WARNING: ヘルスチェックに失敗しました。コンテナを再起動します..."
        docker-compose restart
    else
        log "INFO: システムは正常に動作しています"
    fi
}

check_container_health
EOF

    chmod +x /usr/local/bin/${APP_NAME}-monitor.sh
    
    # cronジョブの設定（5分間隔で監視）
    echo "*/5 * * * * root /usr/local/bin/${APP_NAME}-monitor.sh" > /etc/cron.d/${APP_NAME}-monitor
    
    log "監視スクリプトが作成されました"
}

# ファイアウォール設定
setup_firewall() {
    log "ファイアウォール設定をチェックしています..."
    
    # Amazon Linux/RHEL系の場合
    if command -v firewall-cmd &> /dev/null; then
        firewall-cmd --permanent --add-port=8080/tcp || true
        firewall-cmd --reload || true
    # Ubuntu/Debian系の場合
    elif command -v ufw &> /dev/null; then
        ufw allow 8080/tcp || true
    fi
    
    log "ファイアウォール設定が完了しました"
}

# メイン処理
main() {
    log "デプロイメントを開始します"
    
    check_prerequisites
    install_docker
    install_docker_compose
    setup_app_directory
    
    # 現在のディレクトリからファイルをコピー
    if [ -f "Dockerfile" ] && [ -f "docker-compose.yml" ]; then
        log "アプリケーションファイルをコピーしています..."
        cp -r . "$APP_DIR/"
        cd "$APP_DIR"
    else
        error_exit "Dockerファイルが見つかりません。正しいディレクトリで実行してください"
    fi
    
    create_systemd_service
    setup_log_rotation
    create_monitoring_script
    setup_firewall
    
    # アプリケーションの起動
    log "アプリケーションを起動しています..."
    systemctl start ${APP_NAME}.service
    
    # 起動確認
    sleep 30
    if systemctl is-active --quiet ${APP_NAME}.service; then
        log "デプロイメントが正常に完了しました"
        log "アプリケーションログ: docker-compose -f ${APP_DIR}/${DOCKER_COMPOSE_FILE} logs -f"
        log "ステータス確認: systemctl status ${APP_NAME}.service"
        echo ""
        echo "================================================"
        echo "デプロイメント完了!"
        echo "================================================"
        echo "アプリケーションディレクトリ: $APP_DIR"
        echo "ログ確認: docker-compose -f ${APP_DIR}/${DOCKER_COMPOSE_FILE} logs -f"
        echo "ステータス: systemctl status ${APP_NAME}.service"
        echo "停止: systemctl stop ${APP_NAME}.service"
        echo "再起動: systemctl restart ${APP_NAME}.service"
    else
        error_exit "アプリケーションの起動に失敗しました"
    fi
}

# スクリプト実行
main "$@" 