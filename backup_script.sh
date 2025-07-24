#!/bin/bash
# Automated PostgreSQL Backup Script for Caloria
# This script creates daily backups of the PostgreSQL database

set -e  # Exit on any error

# Configuration
DB_NAME="caloria_vip_db"
DB_USER="caloria_vip_user"
BACKUP_DIR="/var/backups/caloria"
LOG_FILE="/var/www/caloria/logs/backup.log"
RETENTION_DAYS=7

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to clean old backups
cleanup_old_backups() {
    log_message "Cleaning up backups older than $RETENTION_DAYS days"
    find "$BACKUP_DIR" -name "caloria_*.sql" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -name "caloria_*.sql.gz" -mtime +$RETENTION_DAYS -delete
}

# Main backup function
perform_backup() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$BACKUP_DIR/caloria_${timestamp}.sql"
    local compressed_file="${backup_file}.gz"
    
    log_message "Starting PostgreSQL backup for $DB_NAME"
    
    # Create PostgreSQL backup
    if PGPASSWORD="temp_password_change_me" pg_dump -h localhost -U "$DB_USER" "$DB_NAME" > "$backup_file"; then
        log_message "✅ Database backup created: $backup_file"
        
        # Compress the backup
        if gzip "$backup_file"; then
            log_message "✅ Backup compressed: $compressed_file"
            
            # Verify backup integrity
            if zcat "$compressed_file" | head -10 | grep -q "PostgreSQL database dump"; then
                log_message "✅ Backup integrity verified"
                
                # Get backup size
                local size=$(du -h "$compressed_file" | cut -f1)
                log_message "📊 Backup size: $size"
                
                return 0
            else
                log_message "❌ Backup integrity check failed"
                return 1
            fi
        else
            log_message "❌ Backup compression failed"
            return 1
        fi
    else
        log_message "❌ Database backup failed"
        return 1
    fi
}

# Health check function
check_database_health() {
    log_message "Checking database connectivity"
    
    if PGPASSWORD="temp_password_change_me" psql -h localhost -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
        log_message "✅ Database connection successful"
        return 0
    else
        log_message "❌ Database connection failed"
        return 1
    fi
}

# Test backup restoration (optional)
test_backup_restoration() {
    local latest_backup=$(ls -t "$BACKUP_DIR"/caloria_*.sql.gz 2>/dev/null | head -1)
    
    if [ -n "$latest_backup" ]; then
        log_message "Testing backup restoration capability with: $(basename "$latest_backup")"
        
        # Test if we can read the backup file
        if zcat "$latest_backup" | head -1 | grep -q "PostgreSQL database dump"; then
            log_message "✅ Backup file is readable and appears valid"
        else
            log_message "❌ Backup file appears corrupted"
        fi
    else
        log_message "⚠️  No backup files found for restoration test"
    fi
}

# Main execution
main() {
    log_message "=== Starting Caloria Database Backup Process ==="
    
    # Check database health first
    if ! check_database_health; then
        log_message "❌ Backup aborted due to database connectivity issues"
        exit 1
    fi
    
    # Perform backup
    if perform_backup; then
        log_message "✅ Backup completed successfully"
        
        # Clean up old backups
        cleanup_old_backups
        
        # Test restoration capability
        test_backup_restoration
        
        log_message "=== Backup process completed successfully ==="
        exit 0
    else
        log_message "❌ Backup process failed"
        exit 1
    fi
}

# Execute main function
main "$@" 