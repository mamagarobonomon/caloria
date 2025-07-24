"""
Database Service for Caloria Application
Provides optimized database operations with performance monitoring
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import func, text, and_, or_
from sqlalchemy.orm import joinedload, selectinload
from services.logging_service import caloria_logger, LogTimer
from exceptions import DatabaseException
from config.constants import AppConstants

class DatabaseService:
    """Optimized database operations service"""
    
    def __init__(self, db):
        self.db = db
        self.logger = caloria_logger
    
    def create_performance_indexes(self) -> bool:
        """Create database indexes for better performance"""
        try:
            with LogTimer("create_database_indexes"):
                indexes = [
                    # User table indexes
                    "CREATE INDEX IF NOT EXISTS idx_user_whatsapp_id ON user(whatsapp_id)",
                    "CREATE INDEX IF NOT EXISTS idx_user_subscription_status ON user(subscription_status)",
                    "CREATE INDEX IF NOT EXISTS idx_user_created_at ON user(created_at)",
                    "CREATE INDEX IF NOT EXISTS idx_user_quiz_completed ON user(quiz_completed)",
                    
                    # Food log indexes
                    "CREATE INDEX IF NOT EXISTS idx_food_log_user_id ON food_log(user_id)",
                    "CREATE INDEX IF NOT EXISTS idx_food_log_created_at ON food_log(created_at)",
                    "CREATE INDEX IF NOT EXISTS idx_food_log_user_date ON food_log(user_id, created_at)",
                    "CREATE INDEX IF NOT EXISTS idx_food_log_analysis_method ON food_log(analysis_method)",
                    
                    # Daily stats indexes
                    "CREATE INDEX IF NOT EXISTS idx_daily_stats_user_id ON daily_stats(user_id)",
                    "CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_stats(date)",
                    "CREATE INDEX IF NOT EXISTS idx_daily_stats_user_date ON daily_stats(user_id, date)",
                    
                    # System activity log indexes
                    "CREATE INDEX IF NOT EXISTS idx_system_activity_user_id ON system_activity_log(user_id)",
                    "CREATE INDEX IF NOT EXISTS idx_system_activity_created_at ON system_activity_log(created_at)",
                    "CREATE INDEX IF NOT EXISTS idx_system_activity_type ON system_activity_log(activity_type)",
                    
                    # Subscription related indexes
                    "CREATE INDEX IF NOT EXISTS idx_subscription_user_id ON subscription(user_id)",
                    "CREATE INDEX IF NOT EXISTS idx_subscription_status ON subscription(status)",
                    
                    # Payment transaction indexes
                    "CREATE INDEX IF NOT EXISTS idx_payment_transaction_user_id ON payment_transaction(user_id)",
                    "CREATE INDEX IF NOT EXISTS idx_payment_transaction_created_at ON payment_transaction(created_at)",
                    
                    # Composite indexes for common queries
                    "CREATE INDEX IF NOT EXISTS idx_user_active_subscription ON user(is_active, subscription_status)",
                    "CREATE INDEX IF NOT EXISTS idx_food_log_user_today ON food_log(user_id, created_at) WHERE created_at >= CURRENT_DATE"
                ]
                
                with self.db.engine.connect() as conn:
                    for index_sql in indexes:
                        try:
                            conn.execute(text(index_sql))
                            self.logger.info(f"Created index: {index_sql}")
                        except Exception as e:
                            if "already exists" not in str(e).lower():
                                self.logger.warning(f"Index creation failed: {e}")
                    
                    conn.commit()
                
                self.logger.info("Database indexes created successfully")
                return True
                
        except Exception as e:
            self.logger.log_database_error("create_indexes", "multiple", e)
            return False
    
    def get_user_with_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user with aggregated statistics (optimized query)"""
        try:
            with LogTimer("get_user_with_stats") as timer:
                from app import User, FoodLog, DailyStats
                
                # Single query to get user with aggregated stats
                user_stats = self.db.session.query(
                    User,
                    func.count(FoodLog.id).label('total_food_logs'),
                    func.avg(FoodLog.calories).label('avg_calories'),
                    func.max(FoodLog.created_at).label('last_food_log'),
                    func.count(DailyStats.id).label('total_days_logged')
                ).outerjoin(FoodLog).outerjoin(DailyStats).filter(
                    User.id == user_id
                ).group_by(User.id).first()
                
                if not user_stats:
                    return None
                
                user, total_logs, avg_calories, last_log, total_days = user_stats
                
                return {
                    'user': user,
                    'statistics': {
                        'total_food_logs': total_logs or 0,
                        'average_calories': float(avg_calories) if avg_calories else 0,
                        'last_food_log': last_log,
                        'total_days_logged': total_days or 0
                    }
                }
                
        except Exception as e:
            self.logger.log_database_error("get_user_with_stats", "user", e, str(user_id))
            raise DatabaseException(f"Failed to get user statistics: {str(e)}", 
                                   operation="get_user_with_stats", table="user")
    
    def update_daily_stats_optimized(self, user_id: int, target_date: date) -> Dict[str, Any]:
        """Optimized daily stats update using aggregation queries"""
        try:
            with LogTimer("update_daily_stats_optimized") as timer:
                from app import FoodLog, DailyStats, User
                
                # Single aggregation query to get all totals
                daily_totals = self.db.session.query(
                    func.sum(FoodLog.calories).label('total_calories'),
                    func.sum(FoodLog.protein).label('total_protein'),
                    func.sum(FoodLog.carbs).label('total_carbs'),
                    func.sum(FoodLog.fat).label('total_fat'),
                    func.sum(FoodLog.fiber).label('total_fiber'),
                    func.sum(FoodLog.sodium).label('total_sodium'),
                    func.count(FoodLog.id).label('meals_logged'),
                    func.avg(FoodLog.confidence_score).label('avg_confidence')
                ).filter(
                    FoodLog.user_id == user_id,
                    func.date(FoodLog.created_at) == target_date
                ).first()
                
                # Get or create daily stats record
                daily_stats = DailyStats.query.filter_by(
                    user_id=user_id, 
                    date=target_date
                ).first()
                
                if not daily_stats:
                    user = User.query.get(user_id)
                    daily_stats = DailyStats(
                        user_id=user_id,
                        date=target_date,
                        goal_calories=user.daily_calorie_goal if user else 2000
                    )
                    self.db.session.add(daily_stats)
                
                # Update with aggregated values
                daily_stats.total_calories = float(daily_totals.total_calories or 0)
                daily_stats.total_protein = float(daily_totals.total_protein or 0)
                daily_stats.total_carbs = float(daily_totals.total_carbs or 0)
                daily_stats.total_fat = float(daily_totals.total_fat or 0)
                daily_stats.total_fiber = float(daily_totals.total_fiber or 0)
                daily_stats.total_sodium = float(daily_totals.total_sodium or 0)
                daily_stats.meals_logged = daily_totals.meals_logged or 0
                daily_stats.calorie_difference = daily_stats.total_calories - daily_stats.goal_calories
                daily_stats.updated_at = datetime.utcnow()
                
                self.db.session.commit()
                
                return {
                    'daily_stats': daily_stats,
                    'totals': daily_totals,
                    'avg_confidence': float(daily_totals.avg_confidence or 0)
                }
                
        except Exception as e:
            self.db.session.rollback()
            self.logger.log_database_error("update_daily_stats", "daily_stats", e, str(user_id))
            raise DatabaseException(f"Failed to update daily stats: {str(e)}",
                                   operation="update_daily_stats", table="daily_stats")
    
    def get_users_paginated(self, page: int = 1, per_page: int = AppConstants.DEFAULT_PAGE_SIZE,
                           filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get paginated users list with filters (optimized)"""
        try:
            with LogTimer("get_users_paginated") as timer:
                from app import User
                
                query = User.query
                
                # Apply filters
                if filters:
                    if filters.get('is_active') is not None:
                        query = query.filter(User.is_active == filters['is_active'])
                    
                    if filters.get('subscription_status'):
                        query = query.filter(User.subscription_status == filters['subscription_status'])
                    
                    if filters.get('quiz_completed') is not None:
                        query = query.filter(User.quiz_completed == filters['quiz_completed'])
                    
                    if filters.get('created_after'):
                        query = query.filter(User.created_at >= filters['created_after'])
                    
                    if filters.get('search'):
                        search_term = f"%{filters['search']}%"
                        query = query.filter(
                            or_(
                                User.first_name.ilike(search_term),
                                User.last_name.ilike(search_term),
                                User.whatsapp_id.ilike(search_term)
                            )
                        )
                
                # Order by created_at desc for better performance
                query = query.order_by(User.created_at.desc())
                
                # Paginate
                pagination = query.paginate(
                    page=page, 
                    per_page=min(per_page, AppConstants.MAX_PAGE_SIZE),
                    error_out=False
                )
                
                return {
                    'users': pagination.items,
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'current_page': page,
                    'per_page': per_page,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev
                }
                
        except Exception as e:
            self.logger.log_database_error("get_users_paginated", "user", e)
            raise DatabaseException(f"Failed to get paginated users: {str(e)}",
                                   operation="get_users_paginated", table="user")
    
    def get_recent_food_logs_optimized(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Get recent food logs with user info (optimized with joins)"""
        try:
            with LogTimer("get_recent_food_logs") as timer:
                from app import FoodLog, User
                
                # Single query with join to get food logs and user info
                food_logs = self.db.session.query(
                    FoodLog,
                    User.first_name,
                    User.last_name
                ).join(User).order_by(
                    FoodLog.created_at.desc()
                ).limit(limit).all()
                
                return [
                    {
                        'food_log': food_log,
                        'user_name': f"{first_name} {last_name}".strip()
                    }
                    for food_log, first_name, last_name in food_logs
                ]
                
        except Exception as e:
            self.logger.log_database_error("get_recent_food_logs", "food_log", e)
            raise DatabaseException(f"Failed to get recent food logs: {str(e)}",
                                   operation="get_recent_food_logs", table="food_log")
    
    def get_analytics_data_optimized(self) -> Dict[str, Any]:
        """Get analytics data using optimized queries"""
        try:
            with LogTimer("get_analytics_data") as timer:
                from app import User, FoodLog, SystemActivityLog
                
                # Single query to get user statistics
                user_stats = self.db.session.query(
                    func.count(User.id).label('total_users'),
                    func.count(func.nullif(User.quiz_completed, False)).label('quiz_completed'),
                    func.count(func.nullif(User.is_active, False)).label('active_users'),
                    func.count(
                        func.case([(User.subscription_status == 'trial_pending', 1)])
                    ).label('trial_pending'),
                    func.count(
                        func.case([(User.subscription_status == 'trial_active', 1)])
                    ).label('trial_active'),
                    func.count(
                        func.case([(User.subscription_status == 'active', 1)])
                    ).label('paid_subscribers'),
                    func.count(
                        func.case([(User.subscription_status == 'cancelled', 1)])
                    ).label('cancelled')
                ).first()
                
                # Food logs statistics
                food_stats = self.db.session.query(
                    func.count(FoodLog.id).label('total_food_logs'),
                    func.avg(FoodLog.confidence_score).label('avg_confidence'),
                    func.count(func.distinct(FoodLog.user_id)).label('users_with_logs')
                ).first()
                
                # Recent activity (last 7 days)
                week_ago = datetime.utcnow() - timedelta(days=7)
                recent_activity = self.db.session.query(
                    func.count(
                        func.case([(User.created_at >= week_ago, 1)])
                    ).label('recent_signups'),
                    func.count(
                        func.case([(and_(
                            User.trial_start_time >= week_ago,
                            User.trial_start_time.isnot(None)
                        ), 1)])
                    ).label('recent_trials')
                ).first()
                
                # Calculate conversion rates
                total_users = user_stats.total_users or 1  # Avoid division by zero
                quiz_completed = user_stats.quiz_completed or 0
                trial_active = user_stats.trial_active or 0
                
                return {
                    'user_metrics': {
                        'total_users': total_users,
                        'quiz_completed': quiz_completed,
                        'active_users': user_stats.active_users or 0,
                        'trial_pending': user_stats.trial_pending or 0,
                        'trial_active': trial_active,
                        'paid_subscribers': user_stats.paid_subscribers or 0,
                        'cancelled': user_stats.cancelled or 0
                    },
                    'conversion_rates': {
                        'quiz_completion': round((quiz_completed / total_users) * 100, 2),
                        'trial_conversion': round(
                            (trial_active / quiz_completed * 100) if quiz_completed > 0 else 0, 2
                        ),
                        'paid_conversion': round(
                            (user_stats.paid_subscribers / trial_active * 100) if trial_active > 0 else 0, 2
                        )
                    },
                    'food_analytics': {
                        'total_food_logs': food_stats.total_food_logs or 0,
                        'average_confidence': round(float(food_stats.avg_confidence or 0), 2),
                        'users_with_logs': food_stats.users_with_logs or 0
                    },
                    'trends': {
                        'recent_signups_7d': recent_activity.recent_signups or 0,
                        'recent_trials_7d': recent_activity.recent_trials or 0
                    }
                }
                
        except Exception as e:
            self.logger.log_database_error("get_analytics_data", "multiple", e)
            raise DatabaseException(f"Failed to get analytics data: {str(e)}",
                                   operation="get_analytics_data", table="multiple")
    
    def cleanup_old_data(self, days_to_keep: int = 90) -> Dict[str, int]:
        """Clean up old data to maintain performance"""
        try:
            with LogTimer("cleanup_old_data") as timer:
                from app import SystemActivityLog
                
                cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
                
                # Clean up old system activity logs
                deleted_activities = self.db.session.query(SystemActivityLog).filter(
                    SystemActivityLog.created_at < cutoff_date
                ).delete()
                
                # Clean up old temporary files references (if any)
                # This could be extended to clean up other temporary data
                
                self.db.session.commit()
                
                cleanup_results = {
                    'deleted_activity_logs': deleted_activities,
                    'cutoff_date': cutoff_date.isoformat()
                }
                
                self.logger.info("Data cleanup completed", cleanup_results)
                return cleanup_results
                
        except Exception as e:
            self.db.session.rollback()
            self.logger.log_database_error("cleanup_old_data", "multiple", e)
            raise DatabaseException(f"Failed to cleanup old data: {str(e)}",
                                   operation="cleanup_old_data", table="multiple")
    
    def get_database_health(self) -> Dict[str, Any]:
        """Get database health and performance metrics"""
        try:
            with LogTimer("get_database_health") as timer:
                from app import User, FoodLog, DailyStats
                
                health_data = {}
                
                # Basic connectivity test
                with self.db.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                    health_data['connectivity'] = 'healthy'
                
                # Table sizes
                table_sizes = {
                    'users': User.query.count(),
                    'food_logs': FoodLog.query.count(),
                    'daily_stats': DailyStats.query.count()
                }
                health_data['table_sizes'] = table_sizes
                
                # Recent activity
                recent_logs = FoodLog.query.filter(
                    FoodLog.created_at >= datetime.utcnow() - timedelta(hours=24)
                ).count()
                health_data['recent_activity'] = {
                    'food_logs_24h': recent_logs
                }
                
                # Database size estimation (simplified)
                total_records = sum(table_sizes.values())
                health_data['estimated_size'] = {
                    'total_records': total_records,
                    'size_category': 'small' if total_records < 10000 else 
                                   'medium' if total_records < 100000 else 'large'
                }
                
                return health_data
                
        except Exception as e:
            self.logger.log_database_error("get_database_health", "multiple", e)
            return {
                'connectivity': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            } 