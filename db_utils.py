from CTFd.utils.modes import get_model
from .models import (
    Achievement,
    ChallengeAchievementRelationship,
    NotifierConfig,
)

from sqlalchemy import exists
from sqlalchemy.sql import and_

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
    def get_all_achievements_of_challenge(challenge_id: int, session=db.session):
        subquery = exists().where(
            (Achievement.id == ChallengeAchievementRelationship.achievement_id)
            & (ChallengeAchievementRelationship.challenge_id == challenge_id)
        )
        return session.query(Achievement).filter(subquery).all()

    @staticmethod
    def get_achievement_solve_count_for_user(achievement: Achievement, solve: Solves, session=db.session):
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
