import os
import yaml

from flask import redirect, url_for, render_template, request
from flask_login import current_user
from argparse import ArgumentParser
from internal.appl import app
from internal.views import *
from internal.auth import *


@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    else:
        return redirect(url_for("login"))


@app.errorhandler(404)
def not_found(e):
    return render_template("not_found.html")


@app.before_request
def redirect_https():
    if not request.is_secure:
        url = request.url.replace("http://", "https://", 1)
        code = 301
        return redirect(url, code=code)


if __name__ == "__main__":
    parser = ArgumentParser(description="This is a script dashboard system accessible over the web browser.")
    req_group = parser.add_argument_group("required")
    req_group.add_argument("--config", "-c", required=True, type=str, help="JSON configuration file.")
    req_group.add_argument("--crt", required=True, type=str, help="Certificate file.")
    req_group.add_argument("--key", required=True, type=str, help="Private key file.")
    args = parser.parse_args()

    try:
        with open(args.config) as file:
            app.custom_config = yaml.load(file, yaml.FullLoader)
            if not os.path.exists(app.custom_config["workspace"]):
                os.mkdir(app.custom_config["workspace"])

        app.run(host="0.0.0.0", port=5000, ssl_context=(args.crt, args.key))
    except Exception as e:
        print(e)

else:
    with open("config/config.yml") as file:
        app.custom_config = yaml.load(file, yaml.FullLoader)
        if not os.path.exists(app.custom_config["workspace"]):
            os.mkdir(app.custom_config["workspace"])
