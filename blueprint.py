from CTFd.utils.challenges import get_all_challenges
from flask import request, render_template, Blueprint, abort, redirect
from .db_utils import DBAchievements, DBUtils
from CTFd.utils.decorators import admins_only, authed_only

import requests as rq
import tweepy
from .hooks import discord_achievement_notify

notifier_bp = Blueprint("notifier", __name__, template_folder="templates")


def load_bp(plugin_route):
    @notifier_bp.route(plugin_route, methods=["GET"])
    @admins_only
    def get_config():
        config = DBUtils.get_config()
        achievements = DBAchievements.get_all_achievements()
        challenges = get_all_challenges(admin=True)
        user_achievements = DBAchievements.get_all_unlocked_achievements()
        return render_template(
            "ctfd_notifier/config.html",
            config=config,
            achievements=achievements,
            user_achievements=user_achievements,
            challenges=challenges,
        )

    @notifier_bp.route(plugin_route, methods=["POST"])
    @admins_only
    def update_config():
        config = request.form.to_dict()
        del config["nonce"]

        errors = test_config(config)

        if len(errors) > 0:
            return render_template(
                "ctfd_notifier/config.html", config=DBUtils.get_config(), errors=errors
            )
        else:
            DBUtils.save_config(config.items())
            return render_template(
                "ctfd_notifier/config.html", config=DBUtils.get_config()
            )

    @notifier_bp.route(plugin_route + "/achievements", methods=["POST"])
    @admins_only
    def create_achievement():
        achievement = request.form.to_dict()
        achievement["enabled"] = (
            True if achievement.get("enabled", "off") == "on" else False
        )
        del achievement["nonce"]

        chal_ids = request.form.getlist("chall_ids") or []
        achievement["chall_ids"] = [int(x.strip()) for x in chal_ids]

        # Validate here maybe?

        DBAchievements.create_achievement(**achievement)

        return redirect("/admin/notifier", code=302)

    @notifier_bp.route(plugin_route + "/achievements/delete", methods=["POST"])
    @admins_only
    def delete_achievement():
        achievement = request.form.to_dict()
        achievement_id = int(achievement["id"])
        DBAchievements.delete_achievement(id=achievement_id)
        return redirect("/admin/notifier", code=302)

    @notifier_bp.route(plugin_route + "/achievements/toggle_enabled", methods=["POST"])
    @admins_only
    def toggle_enabled_achievement():
        achievement = request.form.to_dict()
        achievement_id = int(achievement["id"])
        DBAchievements.toggle_enabled(id=achievement_id)
        return redirect("/admin/notifier", code=302)

    @notifier_bp.route(plugin_route + "/achievements/run", methods=["POST"])
    @admins_only
    def achievements_run():
        achievements = DBAchievements.create_achievements_for_all_users()
        print(achievements)
        return redirect("/admin/notifier", code=302)

    @notifier_bp.route(plugin_route + "/achievements/notify", methods=["POST"])
    @admins_only
    def achievements_notify():
        form = request.form.to_dict()
        config = DBUtils.get_config()
        user_achievement = DBAchievements.get_user_achievelent_relation(
            form["achievement_user"], form["achievement_id"]
        )
        DBAchievements.update_user_achievement(
            form["achievement_user"], form["achievement_id"], {"notified": True}
        )
        discord_achievement_notify(
            user_achievement[-1],
            user_achievement[-2],
            config.get("discord_webhook_url"),
        )
        return redirect("/admin/notifier", code=302)

    return notifier_bp


def test_config(config):
    errors = list()
    if "discord_notifier" in config:
        if config["discord_notifier"]:
            webhookurl = config["discord_webhook_url"]

            if not webhookurl.startswith(
                "https://discordapp.com/api/webhooks/"
            ) and not webhookurl.startswith("https://discord.com/api/webhooks"):
                errors.append("Invalid Webhook URL!")
            else:
                try:
                    r = rq.get(webhookurl)
                    if not r.status_code == 200:
                        errors.append("Could not verify that the Webhook is working!")
                except rq.exceptions.RequestException as e:
                    errors.append("Invalid Webhook URL!")

    if "twitter_notifier" in config:
        if config["twitter_notifier"]:
            try:
                AUTH = tweepy.OAuthHandler(
                    config.get("twitter_consumer_key"),
                    config.get("twitter_consumer_secret"),
                )
                AUTH.set_access_token(
                    config.get("twitter_access_token"),
                    config.get("twitter_access_token_secret"),
                )
                API = tweepy.API(AUTH)
                API.home_timeline()
            except tweepy.TweepError:
                errors.append("Invalid authentication Data!")

    return errors
