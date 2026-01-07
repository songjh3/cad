#!/bin/bash
# 腾讯云服务器一键部署strongSwan VPN脚本
# 使用方法：sudo bash deploy_strongswan.sh

set -e  # 遇到错误立即退出

echo "🔧 StrongSwan VPN 一键部署脚本"
echo "================================"

# 定义颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 检查root权限
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}❌ 请使用root权限运行此脚本${NC}"
    exit 1
fi

# 获取服务器信息
SERVER_IP=$(curl -s ifconfig.me || hostname -I | awk '{print $1}')
HOSTNAME=$(hostname)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 备份函数
backup_config() {
    if [ -f "$1" ]; then
        cp "$1" "${1}.backup.${TIMESTAMP}"
        echo -e "${GREEN}✓ 已备份: $1${NC}"
    fi
}

echo -e "\n${BLUE}📊 系统信息${NC}"
echo "----------------"
echo "服务器IP: $SERVER_IP"
echo "主机名: $HOSTNAME"

# 1. 安装strongSwan
echo -e "\n${BLUE}🚀 步骤1: 安装strongSwan...${NC}"
if command -v ipsec &> /dev/null; then
    echo -e "${YELLOW}⚠️  strongSwan已安装，跳过安装${NC}"
else
    echo "安装依赖包..."
    yum install -y epel-release
    
    echo "安装strongSwan..."
    yum install -y strongswan
    
    echo -e "${GREEN}✅ strongSwan安装完成${NC}"
    ipsec --version
fi

# 2. 生成VPN配置
echo -e "\n${BLUE}⚙️  步骤2: 配置VPN参数...${NC}"

# 获取用户输入
echo -e "${CYAN}请输入VPN域名（默认: vpn.${HOSTNAME}）:${NC}"
read -p "域名: " VPN_DOMAIN
VPN_DOMAIN=${VPN_DOMAIN:-"vpn.${HOSTNAME}"}

echo -e "${CYAN}请输入VPN用户名（默认: vpnuser）:${NC}"
read -p "用户名: " VPN_USER
VPN_USER=${VPN_USER:-"vpnuser"}

echo -e "${CYAN}请输入VPN密码:${NC}"
read -sp "密码: " VPN_PASS
echo
if [ -z "$VPN_PASS" ]; then
    echo -e "${RED}❌ 密码不能为空${NC}"
    exit 1
fi

echo -e "${CYAN}请输入分配给客户端的IP段（默认: 10.10.10.0/24）:${NC}"
read -p "IP段: " CLIENT_SUBNET
CLIENT_SUBNET=${CLIENT_SUBNET:-"10.10.10.0/24"}

echo -e "${CYAN}请输入DNS服务器（默认: 8.8.8.8,8.8.4.4）:${NC}"
read -p "DNS: " DNS_SERVERS
DNS_SERVERS=${DNS_SERVERS:-"8.8.8.8,8.8.4.4"}

# 3. 生成证书
echo -e "\n${BLUE}🔐 步骤3: 生成SSL证书...${NC}"

# 创建证书目录
mkdir -p /etc/strongswan/ipsec.d/{private,cacerts,certs}
cd /etc/strongswan/ipsec.d

# 生成CA私钥
echo "生成CA私钥..."
ipsec pki --gen --type rsa --size 4096 --outform pem > private/ca-key.pem

# 生成自签名CA证书
echo "生成CA证书..."
ipsec pki --self --ca --lifetime 3650 \
    --in private/ca-key.pem \
    --type rsa --dn "C=CN, O=MyVPN, CN=VPN CA" \
    --outform pem > cacerts/ca-cert.pem

# 生成服务器私钥
echo "生成服务器私钥..."
ipsec pki --gen --type rsa --size 4096 --outform pem > private/server-key.pem

# 生成服务器证书
echo "生成服务器证书..."
ipsec pki --pub --in private/server-key.pem --type rsa | \
    ipsec pki --issue --lifetime 1825 \
    --cacert cacerts/ca-cert.pem \
    --cakey private/ca-key.pem \
    --dn "C=CN, O=MyVPN, CN=${VPN_DOMAIN}" \
    --san "${VPN_DOMAIN}" \
    --flag serverAuth --flag ikeIntermediate \
    --outform pem > certs/server-cert.pem

echo -e "${GREEN}✅ 证书生成完成${NC}"

# 4. 配置strongSwan
echo -e "\n${BLUE}📝 步骤4: 配置strongSwan...${NC}"

# 备份原配置
backup_config /etc/strongswan/ipsec.conf
backup_config /etc/strongswan/ipsec.secrets
backup_config /etc/strongswan/strongswan.conf

# 配置ipsec.conf
cat > /etc/strongswan/ipsec.conf << EOF
config setup
    charondebug="ike 1, knl 1, cfg 0"
    uniqueids=no
    strictcrlpolicy=no

conn %default
    ikelifetime=24h
    keylife=1h
    rekeymargin=3m
    keyingtries=1
    keyexchange=ikev2
    authby=secret
    mobike=no

conn ikev2-eap
    auto=add
    compress=no
    type=tunnel
    left=%any
    leftid=@${VPN_DOMAIN}
    leftcert=server-cert.pem
    leftsendcert=always
    leftsubnet=0.0.0.0/0
    right=%any
    rightid=%any
    rightauth=eap-mschapv2
    rightsourceip=${CLIENT_SUBNET}
    rightdns=${DNS_SERVERS}
    eap_identity=%identity
    ike=aes256-sha1-modp1024,aes128-sha1-modp1024,3des-sha1-modp1024!
    esp=aes256-sha256,aes256-sha1,3des-sha1!
    fragmentation=yes
    dpdaction=clear
    dpddelay=30s
EOF

# 配置ipsec.secrets
cat > /etc/strongswan/ipsec.secrets << EOF
: RSA server-key.pem
: PSK "StrongSwanSecretKey"
${VPN_USER} : EAP "${VPN_PASS}"
EOF

# 配置strongswan.conf
cat > /etc/strongswan/strongswan.conf << EOF
charon {
    load_modular = yes
    plugins {
        include strongswan.d/charon/*.conf
    }
    dns1 = ${DNS_SERVERS%%,*}
    nbns1 = ${DNS_SERVERS%%,*}
}
include strongswan.d/*.conf
EOF

echo -e "${GREEN}✅ 配置文件已生成${NC}"

# 5. 配置防火墙
echo -e "\n${BLUE}🔥 步骤5: 配置防火墙...${NC}"

# 检查firewalld
if systemctl is-active --quiet firewalld; then
    echo "配置firewalld..."
    firewall-cmd --permanent --add-service=ipsec
    firewall-cmd --permanent --add-port=500/udp
    firewall-cmd --permanent --add-port=4500/udp
    firewall-cmd --permanent --add-masquerade
    firewall-cmd --reload
    echo -e "${GREEN}✅ 防火墙配置完成${NC}"
else
    echo -e "${YELLOW}⚠️  firewalld未运行，跳过防火墙配置${NC}"
fi

# 6. 配置内核转发
echo -e "\n${BLUE}🔧 步骤6: 配置内核转发...${NC}"

echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf
echo "net.ipv4.conf.all.accept_redirects = 0" >> /etc/sysctl.conf
echo "net.ipv4.conf.all.send_redirects = 0" >> /etc/sysctl.conf
sysctl -p
echo -e "${GREEN}✅ 内核转发已启用${NC}"

# 7. 启动服务
echo -e "\n${BLUE}🚀 步骤7: 启动strongSwan服务...${NC}"

systemctl restart strongswan
systemctl enable strongswan

sleep 3

# 检查服务状态
if systemctl is-active --quiet strongswan; then
    echo -e "${GREEN}✅ strongSwan服务运行正常${NC}"
else
    echo -e "${RED}❌ strongSwan服务启动失败${NC}"
    systemctl status strongswan
    exit 1
fi

# 8. 生成客户端配置文件
echo -e "\n${BLUE}📱 步骤8: 生成客户端配置...${NC}"

CLIENT_CONFIG="/root/vpn_client_config.txt"
cat > "$CLIENT_CONFIG" << EOF
===============================
StrongSwan VPN 客户端配置
===============================

📡 服务器信息：
----------------
服务器地址: ${VPN_DOMAIN} 或 ${SERVER_IP}
VPN协议: IKEv2
端口: UDP 500, 4500

🔐 认证信息：
----------------
用户名: ${VPN_USER}
密码: ${VPN_PASS}

🔧 Windows 10/11 配置：
----------------
1. 设置 → 网络和Internet → VPN
2. 添加VPN连接
3. 配置如下：
   - VPN提供商: Windows（内置）
   - 连接名称: MyVPN
   - 服务器名称或地址: ${VPN_DOMAIN}
   - VPN类型: IKEv2
   - 登录信息类型: 用户名和密码
   - 用户名: ${VPN_USER}
   - 密码: ${VPN_PASS}

📱 Android 配置：
----------------
1. 设置 → 网络和Internet → VPN
2. 添加VPN
3. 配置如下：
   - 名称: MyVPN
   - 类型: IPSec Xauth PSK
   - 服务器地址: ${VPN_DOMAIN}
   - IPSec标识符: ${VPN_DOMAIN}
   - IPSec预共享密钥: StrongSwanSecretKey
   - 用户名: ${VPN_USER}
   - 密码: ${VPN_PASS}

🍎 iOS/macOS 配置：
----------------
1. 设置 → 通用 → VPN → 添加VPN配置
2. 选择IKEv2
3. 配置如下：
   - 描述: MyVPN
   - 服务器: ${VPN_DOMAIN}
   - 远程ID: ${VPN_DOMAIN}
   - 本地ID: 留空
   - 用户认证: 用户名
   - 用户名: ${VPN_USER}
   - 密码: ${VPN_PASS}
   - 使用证书: 关闭

⚠️ 重要提示：
----------------
1. 首次连接可能需要导入CA证书
2. 确保客户端可以访问UDP 500和4500端口
3. 腾讯云安全组需要开放相应端口

🔧 测试连接：
----------------
sudo ipsec status
sudo ipsec statusall
EOF

echo -e "${GREEN}✅ 客户端配置文件已生成: ${CLIENT_CONFIG}${NC}"

# 9. 显示部署摘要
echo -e "\n${GREEN}🎉 StrongSwan VPN 部署完成！${NC}"
echo "==============================="
echo -e "${YELLOW}📊 部署摘要:${NC}"
echo "----------------"
echo -e "✅ 服务器地址: ${CYAN}${VPN_DOMAIN}${NC}"
echo -e "✅ 服务器IP: ${CYAN}${SERVER_IP}${NC}"
echo -e "✅ VPN用户名: ${CYAN}${VPN_USER}${NC}"
echo -e "✅ VPN密码: ${CYAN}${VPN_PASS}${NC}"
echo -e "✅ 客户端IP段: ${CYAN}${CLIENT_SUBNET}${NC}"
echo -e "✅ DNS服务器: ${CYAN}${DNS_SERVERS}${NC}"
echo -e "✅ 配置文件: ${CYAN}${CLIENT_CONFIG}${NC}"
echo ""
echo -e "${YELLOW}🔧 管理命令:${NC}"
echo "----------------"
echo "查看状态: sudo ipsec status"
echo "重启服务: sudo systemctl restart strongswan"
echo "查看日志: sudo journalctl -u strongswan -f"
echo ""
echo -e "${YELLOW}📱 客户端配置文件位置:${NC}"
echo "----------------"
cat "$CLIENT_CONFIG" | tail -20
echo ""
echo -e "${RED}⚠️  重要: 请保存以上连接信息！${NC}"
echo -e "${RED}⚠️  请确保腾讯云安全组开放UDP 500和4500端口${NC}"

# 10. 测试连接
echo -e "\n${BLUE}🧪 步骤9: 运行连接测试...${NC}"
echo "正在测试VPN服务..."
sleep 2
ipsec status
echo ""
echo -e "${GREEN}✅ 所有配置完成！可以使用客户端连接VPN了${NC}"
