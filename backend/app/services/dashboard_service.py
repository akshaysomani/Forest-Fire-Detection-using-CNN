import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.repositories.dashboard_repository import dashboard_repository
from app.services.analytics_service import analytics_service
from app.services.metrics_optimizer import metrics_optimizer
from app.core.exceptions import DashboardException


class DashboardService:
    async def get_overview(self, db: AsyncSession, current_user: User) -> dict:
        """
        Retrieves high-level summary metrics tailored to the user's role.
        Utilizes caching for quick response times.
        """
        try:
            role_names = [role.name for role in current_user.roles]
            user_id = current_user.id
            
            # Super Admin sees everything
            if "Super Admin" in role_names:
                cache_key = "dashboard_overview_admin"
                
                async def fetch_admin_overview():
                    total_users = await dashboard_repository.get_total_users(db)
                    active_users = await dashboard_repository.get_active_users_count(db)
                    total_images = await dashboard_repository.get_total_uploaded_images(db)
                    accuracy = await dashboard_repository.get_detection_accuracy(db)
                    fire = await dashboard_repository.get_detection_counts_by_label(db, "fire")
                    non_fire = await dashboard_repository.get_detection_counts_by_label(db, "non-fire")
                    return {
                        "total_users": total_users,
                        "active_users": active_users,
                        "total_uploaded_images": total_images,
                        "images_processed": total_images,
                        "fire_detections": fire,
                        "non_fire_detections": non_fire,
                        "detection_accuracy": accuracy
                    }
                
                return await metrics_optimizer.get_or_aggregate(cache_key, fetch_admin_overview, ttl_seconds=30)

            # Forest Officer sees their own uploads and accuracy
            elif "Forest Officer" in role_names:
                cache_key = f"dashboard_overview_officer_{user_id}"
                
                async def fetch_officer_overview():
                    total_images = await dashboard_repository.get_total_uploaded_images(db, user_id=user_id)
                    accuracy = await dashboard_repository.get_detection_accuracy(db, user_id=user_id)
                    fire = await dashboard_repository.get_detection_counts_by_label(db, "fire", user_id=user_id)
                    non_fire = await dashboard_repository.get_detection_counts_by_label(db, "non-fire", user_id=user_id)
                    return {
                        "total_users": 0,  # Hidden
                        "active_users": 0,
                        "total_uploaded_images": total_images,
                        "images_processed": total_images,
                        "fire_detections": fire,
                        "non_fire_detections": non_fire,
                        "detection_accuracy": accuracy
                    }
                
                return await metrics_optimizer.get_or_aggregate(cache_key, fetch_officer_overview, ttl_seconds=30)

            # Emergency Response sees global active alerts and predictions
            elif "Emergency Response Officer" in role_names:
                cache_key = "dashboard_overview_emergency"
                
                async def fetch_emergency_overview():
                    total_images = await dashboard_repository.get_total_uploaded_images(db)
                    accuracy = await dashboard_repository.get_detection_accuracy(db)
                    fire = await dashboard_repository.get_detection_counts_by_label(db, "fire")
                    non_fire = await dashboard_repository.get_detection_counts_by_label(db, "non-fire")
                    return {
                        "total_users": 0,
                        "active_users": 0,
                        "total_uploaded_images": total_images,
                        "images_processed": total_images,
                        "fire_detections": fire,
                        "non_fire_detections": non_fire,
                        "detection_accuracy": accuracy
                    }
                
                return await metrics_optimizer.get_or_aggregate(cache_key, fetch_emergency_overview, ttl_seconds=30)

            # Research Analyst sees model details globally
            elif "Research Analyst" in role_names:
                cache_key = "dashboard_overview_analyst"
                
                async def fetch_analyst_overview():
                    total_images = await dashboard_repository.get_total_uploaded_images(db)
                    accuracy = await dashboard_repository.get_detection_accuracy(db)
                    fire = await dashboard_repository.get_detection_counts_by_label(db, "fire")
                    non_fire = await dashboard_repository.get_detection_counts_by_label(db, "non-fire")
                    return {
                        "total_users": 0,
                        "active_users": 0,
                        "total_uploaded_images": total_images,
                        "images_processed": total_images,
                        "fire_detections": fire,
                        "non_fire_detections": non_fire,
                        "detection_accuracy": accuracy
                    }
                
                return await metrics_optimizer.get_or_aggregate(cache_key, fetch_analyst_overview, ttl_seconds=30)

            # Default viewer role fallback
            else:
                cache_key = "dashboard_overview_viewer"
                
                async def fetch_viewer_overview():
                    total_images = await dashboard_repository.get_total_uploaded_images(db)
                    accuracy = await dashboard_repository.get_detection_accuracy(db)
                    fire = await dashboard_repository.get_detection_counts_by_label(db, "fire")
                    non_fire = await dashboard_repository.get_detection_counts_by_label(db, "non-fire")
                    return {
                        "total_users": 0,
                        "active_users": 0,
                        "total_uploaded_images": total_images,
                        "images_processed": total_images,
                        "fire_detections": fire,
                        "non_fire_detections": non_fire,
                        "detection_accuracy": accuracy
                    }
                
                return await metrics_optimizer.get_or_aggregate(cache_key, fetch_viewer_overview, ttl_seconds=30)

        except Exception as e:
            raise DashboardException(f"Failed to generate dashboard overview: {str(e)}")

    async def get_statistics(self, db: AsyncSession, current_user: User) -> dict:
        """Retrieves detailed dashboard analytics filtered by role settings."""
        try:
            role_names = [role.name for role in current_user.roles]
            user_id = current_user.id

            is_officer = "Forest Officer" in role_names and "Super Admin" not in role_names
            target_user_id = user_id if is_officer else None

            cache_key = f"dashboard_stats_{target_user_id or 'global'}"

            async def fetch_stats():
                total_users = await dashboard_repository.get_total_users(db) if not is_officer else 0
                active_users = await dashboard_repository.get_active_users_count(db) if not is_officer else 0
                total_images = await dashboard_repository.get_total_uploaded_images(db, user_id=target_user_id)
                fire = await dashboard_repository.get_detection_counts_by_label(db, "fire", user_id=target_user_id)
                non_fire = await dashboard_repository.get_detection_counts_by_label(db, "non-fire", user_id=target_user_id)
                accuracy = await dashboard_repository.get_detection_accuracy(db, user_id=target_user_id)
                avg_conf = await dashboard_repository.get_average_confidence(db, user_id=target_user_id)
                model_stats = await analytics_service.get_model_usage_statistics(db)

                return {
                    "total_users": total_users,
                    "active_users": active_users,
                    "total_uploaded_images": total_images,
                    "images_processed": total_images,
                    "fire_detections": fire,
                    "non_fire_detections": non_fire,
                    "detection_accuracy": accuracy,
                    "model_usage_statistics": model_stats,
                    "average_confidence": avg_conf
                }

            return await metrics_optimizer.get_or_aggregate(cache_key, fetch_stats, ttl_seconds=30)

        except Exception as e:
            raise DashboardException(f"Failed to compile dashboard statistics: {str(e)}")

    async def get_user_summary(self, db: AsyncSession) -> dict:
        """Retrieves user metric distributions and user registrations growth trends."""
        try:
            cache_key = "dashboard_user_summary"

            async def fetch_user_summary():
                total_users = await dashboard_repository.get_total_users(db)
                active_users = await dashboard_repository.get_active_users_count(db)
                verified_users = await dashboard_repository.get_verified_users_count(db)
                
                # Fetch role distribution
                raw_dist = await dashboard_repository.get_user_role_distribution(db)
                from app.schemas.dashboard_schema import RoleCount
                role_distribution = [
                    RoleCount(role_name=item[0], count=item[1]) for item in raw_dist
                ]

                # User registration growth trend (30 days)
                growth_trend = await analytics_service.get_user_growth_trend(db, days=30)

                return {
                    "total_users": total_users,
                    "active_users": active_users,
                    "verified_users": verified_users,
                    "role_distribution": role_distribution,
                    "user_growth_trend": growth_trend
                }

            return await metrics_optimizer.get_or_aggregate(cache_key, fetch_user_summary, ttl_seconds=30)

        except Exception as e:
            raise DashboardException(f"Failed to compile user summary statistics: {str(e)}")


dashboard_service = DashboardService()
