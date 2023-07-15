from CTFd.utils.modes import get_model
from .models import (
    Achievement,
    ChallengeAchievementRelationship,
    NotifierConfig,
    user_achievement_association_table,
)

from sqlalchemy import exists
from sqlalchemy.sql import and_
from sqlalchemy import func, insert, update


from CTFd.models import Solves, Users, db, Challenges


class DBUtils:
    DEFAULT_CONFIG = [
        {"key": "discord_notifier", "value": "false"},
        {"key": "discord_webhook_url", "value": ""},
        {"key": "twitter_notifier", "value": "false"},
        {"key": "twitter_consumer_key", "value": ""},
        {"key": "twitter_consumer_secret", "value": ""},
        {"key": "twitter_access_token", "value": ""},
        {"key": "twitter_access_token_secret", "value": ""},
        {"key": "twitter_hashtags", "value": ""},
    ]

    @staticmethod
    def get(key):
        return NotifierConfig.query.filter_by(key=key).first()

    @staticmethod
    def get_config():
        configs = NotifierConfig.query.all()
        result = {}

        for c in configs:
            result[str(c.key)] = str(c.value)

        return result

    @staticmethod
    def save_config(config):
        for c in config:
            q = db.session.query(NotifierConfig)
            q = q.filter(NotifierConfig.key == c[0])
            record = q.one_or_none()

            if record:
                record.value = c[1]
                db.session.commit()
            else:
                config = NotifierConfig(key=c[0], value=c[1])
                db.session.add(config)
                db.session.commit()
        db.session.close()

    @staticmethod
    def load_default():
        for cv in DBUtils.DEFAULT_CONFIG:
            # Query for the config setting
            k = DBUtils.get(cv["key"])
            # If its not created, create it with its default value
            if not k:
                c = NotifierConfig(key=cv["key"], value=cv["value"])
                db.session.add(c)
        db.session.commit()


class DBAchievements:
    @staticmethod
    def get_all_achievements():
        q = db.session.query(Achievement)
        return q.all()

    @staticmethod
    def get_all_unlocked_achievements():
        unlocked_achievements = db.session.query(
            user_achievement_association_table,
            Users,
            Achievement
        ).join(
            Users,
            Users.id == user_achievement_association_table.c.user_id
        ).join(
            Achievement,
            Achievement.id == user_achievement_association_table.c.achievement_id
        ).all()

        return unlocked_achievements

    @staticmethod
    def get_all_achievements_of_challenge(challenge_id: int, session=db.session):
        subquery = exists().where(
            (Achievement.id == ChallengeAchievementRelationship.achievement_id)
            & (ChallengeAchievementRelationship.challenge_id == challenge_id)
        )
        return session.query(Achievement).filter(subquery).all()

    @staticmethod
    def get_achievement_solve_count_for_user(
        achievement: Achievement, solve: Solves, session=db.session
    ):
        q = session.query(Solves)
        q = q.filter(
            and_(
                Solves.user_id == solve.user_id,
                Solves.challenge_id.in_([c.id for c in achievement.challenges]),
            )
        )
        return q.count()

    @staticmethod
    def create_achievement(
        name: str,
        description: str,
        image_url: str,
        enabled: bool,
        chall_ids: list[int] = [],
    ):
        achievement = Achievement(
            name=name, description=description, image_url=image_url, enabled=enabled
        )
        db.session.add(achievement)
        db.session.flush()
        db.session.refresh(achievement)

        challenges = Challenges.query.filter(Challenges.id.in_(chall_ids)).all()
        for challenge in challenges:
            relationship = ChallengeAchievementRelationship(
                challenge=challenge, achievement=achievement
            )
            db.session.add(relationship)
        db.session.commit()

    @staticmethod
    def delete_achievement(id: int):
        q = db.session.query(Achievement)
        q = q.filter(Achievement.id == id)
        record = q.one_or_none()

        if record:
            db.session.delete(record)
            db.session.commit()

    @staticmethod
    def toggle_enabled(id: int):
        q = db.session.query(Achievement)
        q = q.filter(Achievement.id == id)
        record = q.one_or_none()

        if record:
            record.enabled = not record.enabled
            db.session.commit()

    def get_user_achievelent_relation(user_id, achievement_id):
        user_achievement = db.session.query(
            user_achievement_association_table,
            Users,
            Achievement,
            Solves
        ).join(
            Users,
            Users.id == user_achievement_association_table.c.user_id
        ).join(
            Achievement,
            Achievement.id == user_achievement_association_table.c.achievement_id
        ).join(
            Solves,
            Solves.id == user_achievement_association_table.c.solve_id
        ).filter(
            user_achievement_association_table.c.user_id == user_id,
            user_achievement_association_table.c.achievement_id == achievement_id
        ).first()

        return user_achievement
    
    def update_user_achievement(user_id, achievement_id, new_values):
        stmt = update(user_achievement_association_table).where(
            (user_achievement_association_table.c.user_id == user_id) &
            (user_achievement_association_table.c.achievement_id == achievement_id)
        ).values(new_values)

        db.session.execute(stmt)
        db.session.commit()

    @staticmethod
    def create_achievements_for_all_users() -> dict[Users, Achievement]:
        q = db.session.query(Users)
        q = q.filter(Users.hidden != True)
        users = q.all()
        achievements = {
            user: DBAchievements.find_user_achievements(user.id) for user in users
        }
        for user, achievements in achievements.items():
            for achievement in achievements:
                print(DBAchievements.get_latest_solve_for_achievement(user.id, achievement.id))
                stmt = insert(user_achievement_association_table).values(
                    achievement_id=achievement.id,
                    user_id=user.id,
                    solve_id=DBAchievements.get_latest_solve_for_achievement(user.id, achievement.id),
                    notified=False,
                )
                db.session.execute(stmt)
        db.session.commit()
        return achievements

    def get_latest_solve_for_achievement(user_id, achievement_id):
        # Get the latest solve that made the user get the achievement
        latest_solve = db.session.query(Solves.id).join(
            ChallengeAchievementRelationship, 
            Solves.challenge_id == ChallengeAchievementRelationship.challenge_id
        ).filter(
            Solves.user_id == user_id,
            ChallengeAchievementRelationship.achievement_id == achievement_id
        ).order_by(
            Solves.id.desc()  # Assuming that higher IDs mean more recent solves
        ).first()

        # The result is a tuple, so we return the first element
        return latest_solve[0] if latest_solve else None

    @staticmethod
    def find_user_achievements(user_id: int) -> Achievement:
        # Query to get the count of challenges per achievement
        challenge_counts = (
            db.session.query(
                ChallengeAchievementRelationship.achievement_id,
                func.count(ChallengeAchievementRelationship.achievement_id).label(
                    "count"
                ),
            )
            .group_by(ChallengeAchievementRelationship.achievement_id)
            .subquery()
        )

        # Query to get the count of challenges solved per achievement for a user
        user_challenge_counts = (
            db.session.query(
                ChallengeAchievementRelationship.achievement_id,
                func.count(Solves.challenge_id).label("user_count"),
            )
            .join(
                Solves,
                ChallengeAchievementRelationship.challenge_id == Solves.challenge_id,
            )
            .filter(Solves.user_id == user_id)
            .group_by(ChallengeAchievementRelationship.achievement_id)
            .subquery()
        )

        # Main query
        achievements = (
            db.session.query(Achievement)
            .join(challenge_counts, Achievement.id == challenge_counts.c.achievement_id)
            .join(
                user_challenge_counts,
                Achievement.id == user_challenge_counts.c.achievement_id,
            )
            .filter(
                user_challenge_counts.c.user_count == challenge_counts.c.count,
                Achievement.enabled == True,
            )
            .all()
        )

        return achievements
