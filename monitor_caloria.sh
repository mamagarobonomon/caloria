#!/bin/bash
# Caloria Domain & Port Monitoring Script
# Prevents other applications from hijacking caloria.vip

echo "🔍 Caloria Domain & Port Monitor"
echo "================================"

# Check if port 5001 is used by the correct application
check_port_ownership() {
    local port=5001
    local expected_user="caloria"
    
    PID=$(lsof -ti :$port 2>/dev/null)
    if [ -n "$PID" ]; then
        ACTUAL_USER=$(ps -o user= -p $PID 2>/dev/null | tr -d ' ')
        if [ "$ACTUAL_USER" != "$expected_user" ]; then
            echo "❌ PORT CONFLICT: Port $port is used by '$ACTUAL_USER', expected '$expected_user'"
            echo "🔧 Process details:"
            ps -fp $PID
            return 1
        else
            echo "✅ Port $port correctly used by '$expected_user'"
        fi
    else
        echo "⚠️ Port $port is not in use"
        return 1
    fi
}

# Check if caloria.vip serves the correct application
check_domain_content() {
    local domain="https://caloria.vip"
    
    # Test for Caloria-specific content
    RESPONSE=$(curl -s $domain | head -20)
    
    if echo "$RESPONSE" | grep -q "Caloria.*Nutrición\|Caloria.*Nutrition"; then
        echo "✅ Domain $domain serves correct Caloria content"
    else
        echo "❌ DOMAIN HIJACK: $domain serves wrong content!"
        echo "📄 Response preview:"
        echo "$RESPONSE" | head -5
        return 1
    fi
    
    # Check HTTP headers for Flask indicators
    HEADERS=$(curl -sI $domain)
    if echo "$HEADERS" | grep -q "X-Powered-By: Express"; then
        echo "❌ WRONG APP: Domain serves Express.js instead of Flask!"
        return 1
    fi
}

# Check SSL certificate validity
check_ssl_certificate() {
    local domain="caloria.vip"
    
    if certbot certificates 2>/dev/null | grep -q "$domain"; then
        echo "✅ SSL certificate exists for $domain"
        
        # Check if certificate is properly configured in nginx
        if nginx -T 2>/dev/null | grep -q "ssl_certificate.*$domain"; then
            echo "✅ SSL properly configured in nginx"
        else
            echo "⚠️ SSL certificate exists but may not be configured in nginx"
        fi
    else
        echo "❌ SSL certificate missing for $domain"
        return 1
    fi
}

# Main monitoring checks
echo "🔍 Running monitoring checks..."
echo ""

ISSUES=0

echo "1. Checking port ownership..."
check_port_ownership || ISSUES=$((ISSUES + 1))
echo ""

echo "2. Checking domain content..."
check_domain_content || ISSUES=$((ISSUES + 1))
echo ""

echo "3. Checking SSL certificate..."
check_ssl_certificate || ISSUES=$((ISSUES + 1))
echo ""

# Summary
if [ $ISSUES -eq 0 ]; then
    echo "✅ ALL CHECKS PASSED: Caloria deployment is healthy!"
    exit 0
else
    echo "❌ $ISSUES ISSUES DETECTED: Manual intervention required!"
    echo ""
    echo "🔧 Suggested fixes:"
    echo "1. Restart Caloria: sudo supervisorctl restart caloria-vip"
    echo "2. Fix SSL config: sudo certbot --nginx -d caloria.vip --redirect"
    echo "3. Check nginx: sudo nginx -t && sudo systemctl reload nginx"
    exit 1
fi 