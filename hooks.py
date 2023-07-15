import json

import requests as rq
from sqlalchemy.event import listen
from sqlalchemy import text

import CTFd.cache as cache
from CTFd.models import Challenges, Solves, Teams, Users
from CTFd.utils.config import is_teams_mode

from ...utils.modes import get_model
from .db_utils import DBAchievements, DBUtils


def discord_notify(solve, webhookurl, first_blood=False):
    text = _getText(solve, first_blood=first_blood)

    embed = {"title": "✅ Solved!", "color": 2278750, "description": text}
    if first_blood:
        embed = {"title": "🩸 First Blood!", "color": 15158332, "description": text}

    data = {"embeds": [embed]}

    try:
        rq.post(
            webhookurl,
            data=json.dumps(data),
            headers={"Content-Type": "application/json"},
        )
    except rq.exceptions.RequestException as e:
        print(e)


def discord_achievement_notify(solve, achievement, webhookurl):
    text = _getAchievementText(solve, achievement)

    embed = {
        "title": "🏆 Achievement Unlocked!",
        "color": 0xF1C40F,
        "description": text,
        "thumbnail": {"url": achievement.image_url},
    }

    data = {"embeds": [embed]}

    try:
        rq.post(
            webhookurl,
            data=json.dumps(data),
            headers={"Content-Type": "application/json"},
        )
    except rq.exceptions.RequestException as e:
        print(e)


def on_solve(mapper, conn, solve):
    config = DBUtils.get_config()
    solves = _getSolves(solve.challenge_id)

    if config.get("discord_notifier") == "true":
        if solves == 1:
            discord_notify(solve, config.get("discord_webhook_url"), first_blood=True)
        elif solves > 0:
            discord_notify(solve, config.get("discord_webhook_url"))

    chall_achievements = DBAchievements.get_all_achievements_of_challenge(
        solve.challenge_id
    )
    for achievement in chall_achievements:
        if _has_solved_all_for(achievement, solve):
            conn.execute(
                text(
                    "INSERT INTO user_achievement_relationship (achievement_id, user_id, solve_id, notified, created_at) VALUES (:achievement_id, :user_id, :solve_id, :notified, CURRENT_TIMESTAMP)"
                ),
                {
                    "achievement_id": achievement.id,
                    "user_id": solve.user_id,
                    "solve_id": solve.id,
                    "notified": config.get("discord_notifier") == "true",
                },
            )
            if config.get("discord_notifier") == "true":
                discord_achievement_notify(
                    solve, achievement, config.get("discord_webhook_url")
                )


def _has_solved_all_for(achievement, solve):
    solve_count = DBAchievements.get_achievement_solve_count_for_user(
        achievement, solve
    )
    # if true, they solved all of the challenges in this achievement
    return solve_count == len(achievement.challenges)


# def _getAchievements(challenge_id):
#     # get all enabled achievements that include this challenge
#     chall_achievements = Achievement.query.filter(
#         Challenges.id==challenge_id, Achievement.enabled==True
#     ).all()
#     achievements = db.session.query(Achievement).filter(subquery).all()
#     return [a.achievement for a in chall_achievements]


def _getSolves(challenge_id):
    Model = get_model()

    solve_count = (
        Solves.query.join(Model, Solves.account_id == Model.id)
        .filter(
            Solves.challenge_id == challenge_id,
            Model.hidden == False,
            Model.banned == False,
        )
        .count()
    )

    return solve_count


def _getChallenge(challenge_id):
    challenge = Challenges.query.filter_by(id=challenge_id).first()
    return challenge


def _getUser(user_id):
    user = Users.query.filter_by(id=user_id).first()
    return user


def _getTeam(team_id):
    team = Teams.query.filter_by(id=team_id).first()
    return team


def _getText(solve, first_blood=False):
    name = ""
    score = 0
    place = 0
    cache.clear_standings()
    user = _getUser(solve.user_id)
    challenge = _getChallenge(solve.challenge_id)

    if is_teams_mode():
        team = _getTeam(user.team_id)
        name = team.name
        score = team.get_score()
        place = team.get_place()
    else:
        name = user.name
        score = user.get_score()
        place = user.get_place()

    if first_blood:
        text = f"{name} got first blood on {challenge.name} and is now in {place} place with {score} points!"
    else:
        text = f"{name} solved {challenge.name} and is now in {place} place with {score} points!"

    return text


def _getAchievementText(solve, achievement):
    name = ""
    user = _getUser(solve.user_id)

    if is_teams_mode():
        team = _getTeam(user.team_id)
        name = team.name
    else:
        name = user.name

    text = f"{name} has achieved {achievement.name}: {achievement.description}!"

    return text


def load_hooks():
    listen(Solves, "after_insert", on_solve)
