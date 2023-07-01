from CTFd.models import (
    db,
)


class NotifierConfig(db.Model):
    key = db.Column(db.String(length=128), primary_key=True)
    value = db.Column(db.Text)

    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __repr__(self):
        return "<NotifierConfig (0) {1}>".format(self.key, self.value)

class Achievement(db.Model):
    __tablename__ = "achievements"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True) 
    name = db.Column(db.Text)
    description = db.Column(db.Text)
    image_url  = db.Column(db.Text)
    enabled = db.Column(db.Boolean, default=False)

    challenges = db.relationship(
        "ChallengeAchievementRelationship", back_populates="achievement", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return "<Achievement {0}>".format(self.name)


class ChallengeAchievementRelationship(db.Model):
    id = db.Column(
        None, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    achievement_id = db.Column(None, db.ForeignKey("achievements.id"))

    achievement = db.relationship("Achievement", foreign_keys="ChallengeAchievementRelationship.achievement_id", lazy="select")