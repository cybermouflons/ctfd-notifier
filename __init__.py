from flask import render_template

import json
import os
from .blueprint import load_bp
from .models import NotifierConfig
from .hooks import load_hooks
from .db_utils import DBUtils, DBAchievements

from CTFd.utils import config
from CTFd.utils.config.visibility import scores_visible
from CTFd.utils.decorators.visibility import (
    check_account_visibility,
    check_score_visibility,
)
from CTFd.utils.helpers import get_infos
from CTFd.utils.scores import get_standings
from CTFd.utils.user import is_admin

PLUGIN_PATH = os.path.dirname(__file__)
CONFIG = json.load(open(f"{PLUGIN_PATH}/config.json"))


def load(app):
    app.db.create_all()  # Create all DB entities
    DBUtils.load_default()
    bp = load_bp(CONFIG["route"])  # Load blueprint
    app.register_blueprint(bp)  # Register blueprint to the Flask app
    load_hooks()

    # override scoreboard to show the "neon" the scoreboard, but with achievements
    # TODO: figure out how to make it use the current theme instead of hardcoding "neon"
    app.view_functions['scoreboard.listing'] = scoreboard_with_achievements


@check_account_visibility
@check_score_visibility
def scoreboard_with_achievements():
    infos = get_infos()

    if config.is_scoreboard_frozen():
        infos.append("Scoreboard has been frozen")

    if is_admin() is True and scores_visible() is False:
        infos.append("Scores are not currently visible to users")

    user_achievements = DBAchievements.get_all_unlocked_achievements()
    standings = get_standings()
    return render_template("ctfd_notifier/scoreboard.html", standings=standings, infos=infos, user_achievements=user_achievements)