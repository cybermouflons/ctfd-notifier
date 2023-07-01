from CTFd.models import db

user_achievement_association_table = db.Table('user_achievement_relationship', 
    db.Column('achievement_id', db.Integer, db.ForeignKey('achievements.id', ondelete='CASCADE')),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE')),
    db.Column('solve_id', db.Integer, db.ForeignKey('solves.id', ondelete='CASCADE')),
    db.Column('created_at', db.DateTime, default=db.func.now())
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
    image_url = db.Column(db.Text)
    enabled = db.Column(db.Boolean, default=False)

    challenges = db.relationship(
        "Challenges",
        secondary="challenge_achievement_relationship",
        cascade="all",
    )
    users = db.relationship(
        "Users",
        secondary="user_achievement_relationship",
        cascade="all",
    )

    def __repr__(self):
        return "<Achievement {0}>".format(self.name)

class ChallengeAchievementRelationship(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    challenge_id = db.Column(None, db.ForeignKey("challenges.id", ondelete="CASCADE"))
    achievement_id = db.Column(None, db.ForeignKey("achievements.id"))

    achievement = db.relationship(
        "Achievement",
        foreign_keys="ChallengeAchievementRelationship.achievement_id",
        lazy="select",
    )
    challenge = db.relationship(
        "Challenges",
        foreign_keys="ChallengeAchievementRelationship.challenge_id",
        lazy="select",
    )
