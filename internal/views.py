import os
import re
import yaml
import shutil
import subprocess
from internal.shell import Shell
from flask import render_template, request, redirect, url_for, send_from_directory
from flask_login import login_required, current_user
from internal.appl import app

SYSTEM_SHELL: Shell = Shell(working_directory='/')

SYSTEMD_CONFIG = {
    'none': [
        {
            'name': "InitialState",
            "options": ["enabled", "started"]
        },
    ],
    'Unit': [
        {
            'name': "Description",
            'placeholder': "Human readable title of the unit. (Required)",
            'required': True
        },
        {
            "name": "Documentation",
            "placeholder": "A space-separated list of URIs referencing documentation for this unit."
        },
        {
            "name": "Wants",
            "placeholder": "Weak requirement dependencies on other units."
        },
        {
            "name": "Requires",
            "placeholder": "Strong requirement dependencies on other units."
        },
        {
            "name": "Requisite",
            "placeholder": "Units required to be started upfront else fails."
        },
        {
            "name": "BindsTo",
            "placeholder": "Like 'Requires' but also stops unit if specified units are stopped."
        },
        {
            "name": "PartOf",
            "placeholder": "Start and stop of specified units will also start and stop this unit."
        },
        {
            "name": "Conflicts",
            "placeholder": "List of unit names that can not run simultanously."
        },
        {
            "name": "Before",
            "placeholder": "Start this unit before specified units."
        },
        {
            "name": "After",
            "placeholder": "Start this unit after specified units."
        },
        {
            "name": "OnFailure",
            "placeholder": "List of units started on failure of this unit."
        },
        {
            "name": "OnSuccess",
            "placeholder": "List of units activated when this unit enters state 'inactive'."
        },
    ],
    "Install": [
        {
            "name": "WantedBy",
            "placeholder": "List of units that have 'wants' dependencies to this unit.",
            "default": "default.target"
        },
        {
            "name": "RequiredBy",
            "placeholder": "List of units that have 'required' dependencies to this unit."
        },
        {
            "name": "UpheldBy",
            "placeholder": "List of units that have 'upheld' dependencies to this unit."
        },
    ],
    "Service": [
        {
            "name": "WorkingDirectory",
            "placeholder": "Relative path to the script root. Defaults to '.'."
        },
        {
            "name": "Type",
            "options": ["simple", "exec", "forking", "oneshot", "dbus", "notify", "notify-reload", "idle"]
        },
        {
            "name": "ExitType",
            "options": ["main", "cgroup"]
        },
        {
            "name": "RemainAfterExit",
            "options": ["no", "yes"]
        },
        {
            "name": "Restart",
            "options": ["no", "on-success", "on-failure", "on-abnormal", "on-watchdog", "on-abort", "always"]
        },
        {
            "name": "RestartSec",
            "placeholder": "Configures the time to sleep before restarting the service."
        },
        {
            "name": "NotifyAccess",
            "options": ["none", "main", "exec", "all"]
        }
    ]
}


def create_dir_if_not_exist(path):
    if not os.path.exists(path):
        os.mkdir(path)


def list_files(path):
    create_dir_if_not_exist(path)
    files = []
    env_dir = os.path.join(path, ".env")
    for root, dnames, fnames in os.walk(path):
        if not root.startswith(env_dir) and "__pycache__" not in root:
            files += [os.path.join(root, f)[len(path) + 1:] for f in fnames]
    return files


def list_dir(path):
    create_dir_if_not_exist(path)
    files = [f for f in os.listdir(path) if f != ".env"]
    return files if files is not None else []


@app.route("/home")
@login_required
def home():
    username = current_user.id
    updates = None
    with open('config/updates.yml', 'r') as f:
        updates = yaml.load(f, yaml.FullLoader)
    scripts = list_dir(os.path.join(app.custom_config['workspace'], username))
    return render_template('home.html', username=current_user.id, scripts=scripts, updates=updates['updates'])


def enable_service(id, enable: bool):
    username = current_user.id
    script_dir = os.path.join(app.custom_config['workspace'], username, id)
    if os.path.exists(script_dir):
        with open(os.path.join(script_dir, '.env/config.yml'), 'r') as f:
            config = yaml.load(f, yaml.FullLoader)
            if config['scheduling'] == 'systemd':
                service_file = f"{username}_{id}_generated.service"
                if not enable:
                    SYSTEM_SHELL.run([['systemctl', 'stop', service_file.lower()]])
                returncode, output = SYSTEM_SHELL.check_output(['systemctl', 'enable' if enable else "disable", service_file.lower()])
                if returncode == 0:
                    return {'id': id, 'success': True}
                else:
                    return {'id': id, 'success': False}
            elif config['scheduling'] == 'crontab':
                crontab_file = os.path.join(app.custom_config['crontab'], f"{username}_{id}_generated".lower())
                if enable:
                    shutil.copy2(os.path.join(script_dir, '.env', f"{username}_{id}_generated".lower()), crontab_file)
                else:
                    if os.path.exists(crontab_file):
                        os.remove(crontab_file)
                    return {'id': id, 'success': not os.path.exists(crontab_file)}

    return {'id': id, 'success': False}


@app.route("/enable/<id>", methods=["GET"])
@login_required
def enable(id):
    return enable_service(id, True)


@app.route("/disable/<id>", methods=["GET"])
@login_required
def disable(id):
    return enable_service(id, False)


def start_service(id, start: bool):
    username = current_user.id
    script_dir = os.path.join(app.custom_config['workspace'], username, id)
    if os.path.exists(script_dir):
        with open(os.path.join(script_dir, '.env/config.yml'), 'r') as f:
            config = yaml.load(f, yaml.FullLoader)
            if config['scheduling'] == 'systemd':
                service_file = f"{username}_{id}_generated.service"
                returncode, output = SYSTEM_SHELL.check_output(['systemctl', 'start' if start else "stop", service_file.lower()])
                if returncode == 0:
                    return {'id': id, 'success': True}
                else:
                    return {'id': id, 'success': False}

    return {'id': id, 'success': False}


@app.route("/start/<id>", methods=["GET"])
@login_required
def start(id):
    return start_service(id, True)


@app.route("/stop/<id>", methods=["GET"])
@login_required
def stop(id):
    return start_service(id, False)


@app.route("/status/<id>", methods=["GET"])
@login_required
def status(id):
    username = current_user.id
    script_dir = os.path.join(app.custom_config['workspace'], username, id)
    if os.path.exists(script_dir):
        with open(os.path.join(script_dir, '.env/config.yml'), 'r') as f:
            config = yaml.load(f, yaml.FullLoader)
            if config['scheduling'] == 'systemd':
                service_file = f"{username}_{id}_generated.service"
                returncode, active_output = SYSTEM_SHELL.check_output(['systemctl', 'is-active', service_file.lower()])
                active_output = active_output.replace('\n', '')
                returncode, enable_output = SYSTEM_SHELL.check_output(['systemctl', 'is-enabled', service_file.lower()])
                enable_output = enable_output.replace('\n', '')
                return {'id': id, 'active': active_output, 'enable': enable_output}
            elif config['scheduling'] == 'crontab':
                crontab_file = os.path.join(app.custom_config['crontab'], f"{username}_{id}_generated".lower())
                if os.path.exists(crontab_file):
                    return {'id': id, 'active': 'active', 'enable': 'enabled'}
                else:
                    return {'id': id, 'active': 'inactive', 'enable': 'disabled'}
            else:
                return {'id': id, 'active': 'active', 'enable': 'enabled'}

    return {'id': id, 'active': 'unknown', 'enable': 'unknown'}


@app.route("/log/<id>", methods=["GET"])
@login_required
def log(id):
    username = current_user.id
    script_dir = os.path.join(app.custom_config['workspace'], username, id)
    if os.path.exists(script_dir):
        with open(os.path.join(script_dir, '.env/config.yml'), 'r') as f:
            config = yaml.load(f, yaml.FullLoader)
            if config['scheduling'] == 'systemd':
                service_file = f"{username}_{id}_generated.service"
                returncode, output = SYSTEM_SHELL.check_output(['journalctl', '-n', '100', '-u', service_file.lower()])
                return {'log': output}
            else:
                output_file = os.path.join(script_dir, 'output.log')
                returncode, output = SYSTEM_SHELL.check_output(['tail', '-n', '100', output_file])
                return {'log': output}
    return {'log': ''}


@app.route("/script/<id>", methods=["GET"])
@login_required
def script(id):
    username = current_user.id
    scripts = list_dir(os.path.join(app.custom_config['workspace'], username))
    script_dir = os.path.join(app.custom_config['workspace'], username, id)
    if os.path.exists(script_dir):
        with open(os.path.join(script_dir, '.env/config.yml'), 'r') as f:
            config = yaml.load(f, yaml.FullLoader)
            config['files'] = list_files(script_dir)
            return render_template('script.html', username=current_user.id, config=config, systemd=SYSTEMD_CONFIG, scripts=scripts, interpreters=app.custom_config['interpreters'])

    return redirect(url_for('home'))


@app.route("/script/new")
@login_required
def new_script():
    username = current_user.id
    scripts = list_dir(os.path.join(app.custom_config['workspace'], username))
    return render_template('script.html', username=current_user.id, config=dict(), systemd=SYSTEMD_CONFIG, scripts=scripts, interpreters=app.custom_config['interpreters'])


def script_dir_delete(username, id):
    script_dir = os.path.join(app.custom_config['workspace'], f"{username}/{id}")
    if os.path.exists(script_dir):
        shutil.rmtree(script_dir)
    crontab_file = os.path.join(app.custom_config['crontab'], f"{username}_{id}_generated")
    if os.path.exists(crontab_file):
        os.remove(crontab_file)
    systemd_file = os.path.join(app.custom_config['systemd'], f"{username}_{id}_generated.service".lower())
    if os.path.exists(systemd_file):
        os.remove(systemd_file)


@app.route("/delete/<id>")
@login_required
def delete(id):
    username = current_user.id
    script_dir_delete(username, id)
    return redirect(url_for('home'))


@app.route("/execute/<id>", methods=['GET', 'POST'])
@login_required
def execute(id):
    if request.method != 'POST':
        pass

    username = current_user.id
    scripts = list_dir(os.path.join(app.custom_config['workspace'], username))
    working_dir = os.path.join(app.custom_config['workspace'], username, id)
    script = os.path.join(working_dir, ".env", "execute.sh")
    if os.path.exists(script):
        with open(os.path.join(working_dir, '.env/config.yml'), 'r') as f:
            config = yaml.load(f, yaml.FullLoader)
            try:
                output = ''
                if config['scheduling'] == 'systemd':
                    service_file = f"{username}_{id}_generated.service"
                    returncode, output = SYSTEM_SHELL.check_output(['systemctl', 'is-active', service_file.lower()])
                    output = output.replace('\n', '')
                if output != 'active':
                    shell = Shell(working_directory=working_dir, env=config['environment'], log_dir=os.path.join(working_dir, '.env'))
                    ret = shell.run([['su', '-', username, '-c', f"bash {script}"]])
                    if ret != 0:
                        config['error'] = f"Execution failed. Check configuration and/or upload a new version. su - {username} -c \"bash {script}\""
            except subprocess.TimeoutExpired:
                config['error'] = 'Execution timed out. All manual execution has a timeout of 5 seconds.'
            config['files'] = list_files(working_dir)
            return render_template('script.html', username=current_user.id, config=config, systemd=SYSTEMD_CONFIG, scripts=scripts, interpreters=app.custom_config['interpreters'])

    return redirect(url_for('home'))


def get_str_or(value: str, default: str):
    if value is not None and value != "":
        return value
    else:
        return default


def write_if(file, tag, config):
    if tag.lower() in config and config[tag.lower()] is not None and config[tag.lower()] != "":
        file.write(f"{tag}={config[tag.lower()]}\n")


def get_config_from_form(request):
    status = True

    config = {
        'username': current_user.id,
        'name': request.form.get('name'),
        'oldName': request.form.get('old-name'),
        'executable': request.form.get('executable'),
        'interpreter': {
            'name': request.form.get('interpreter'),
            'command': app.custom_config['interpreters'][request.form.get('interpreter')]['command']
        },
        'environment': dict(e for e in zip(request.form.getlist('env_name'), request.form.getlist('env_value'))),
        'scheduling': request.form.get('scheduling'),
        'install': request.form.get('install-script'),
        'files': [f for f in request.files.getlist('files') if f.filename != ''],
        'filesToRemove': [f for f in request.form.getlist('file-remove') if f != ''],
        'arguments': request.form.get('cli-args'),
        'service-args': request.form.get('cli-service-args')
    }

    if config['scheduling'] == 'systemd':
        config['systemd'] = dict()
        for entry in SYSTEMD_CONFIG:
            config['systemd'][entry] = dict()
            for value in SYSTEMD_CONFIG[entry]:
                var = value["name"].lower()
                form_value = request.form.get(f"systemd-{var}")
                if 'options' in value and form_value not in value['options']:
                    status = False
                else:
                    config['systemd'][entry][var] = request.form.get(f"systemd-{var}")

    elif config['scheduling'] == 'crontab':
        config['crontab'] = {
            'minute': get_str_or(request.form.get('minute').replace(' ', ''), '*'),
            'hour': get_str_or(request.form.get('hour').replace(' ', ''), '*'),
            'day': get_str_or(request.form.get('day').replace(' ', ''), '*'),
            'month': get_str_or(request.form.get('month').replace(' ', ''), '*'),
            'weekday': get_str_or(request.form.get('weekday').replace(' ', ''), '*')
        }
    elif config['scheduling'] == 'none':
        pass
    else:
        status = False

    if not re.search('^[a-zA-Z0-9_\\-]+$', config['name']):
        config['error'] = "Name contains invalid characters. Only use characters, numerics, '-' and '_'. Whitespaces are not allowed."
        status = False

    return status, config


@app.route("/download/<id>", methods=["GET", "POST"])
@login_required
def download(id):
    script_dir = os.path.join(app.custom_config['workspace'], current_user.id, id)
    files = list_dir(script_dir)
    tar = f"{current_user.id}_{id}.tar.gz"
    shell: Shell = Shell(working_directory=script_dir)
    returncode, output = shell.check_output(['tar', '-czvf', os.path.join("/tmp/", tar)] + files)
    return send_from_directory(directory="/tmp/", path=tar, as_attachment=True)


@app.route("/script/<id>", methods=['POST'])
@login_required
def upload(id):
    if request.method != 'POST':
        pass

    # Extract configuration from form
    status, config = get_config_from_form(request)
    workspace = os.path.join(app.custom_config['workspace'], config['username'])
    scripts = list_dir(workspace)

    if not status:
        config['error'] = 'Invalid form data provided. Please check the inputs.'
        return render_template('script.html', username=current_user.id, config=config, systemd=SYSTEMD_CONFIG, scripts=scripts, interpreters=app.custom_config['interpreters'])

    if config['oldName'] is not None and id != config['oldName'] and id.lower() != config['oldName'].lower() and id.lower() in [s.lower() for s in scripts]:
        config['error'] = 'Specified name is already taken. Please change it and try again.'
        return render_template('script.html', username=current_user.id, config=config, systemd=SYSTEMD_CONFIG, scripts=scripts, interpreters=app.custom_config['interpreters'])

    if config['oldName'] is None and id.lower() in [s.lower() for s in scripts]:
        config['error'] = 'Specified name is already taken. Please change it and try again.'
        return render_template('script.html', username=current_user.id, config=config, systemd=SYSTEMD_CONFIG, scripts=scripts, interpreters=app.custom_config['interpreters'])

    # Check if relative path leaves root directory
    executable_path = os.path.abspath(os.path.join(workspace, config['name'], config['executable'])) if config['executable'] != '' else ''
    if executable_path != "" and not executable_path.startswith(os.path.join(workspace, config['name'])):
        config['error'] = 'Entry point is invalid. You can not leave the root directory.'
        return render_template('script.html', username=current_user.id, config=config, systemd=SYSTEMD_CONFIG, scripts=scripts, interpreters=app.custom_config['interpreters'])
    elif (config['interpreter']['name'] in ["Native", "System"]) and executable_path == "":
        config['error'] = "Interpreter type 'Native' and 'System' require that you specify an executable."
        return render_template('script.html', username=current_user.id, config=config, systemd=SYSTEMD_CONFIG, scripts=scripts, interpreters=app.custom_config['interpreters'])

    if "systemd" in config:
        working_dir = os.path.abspath(os.path.join(workspace, config['name'], config['systemd']['Service']['workingdirectory']))
        if not working_dir.startswith(os.path.join(workspace, config['name'])):
            config['error'] = 'Working directory of systemd configuration out of script root directory.'
            return render_template('script.html', username=current_user.id, config=config, systemd=SYSTEMD_CONFIG, scripts=scripts, interpreters=app.custom_config['interpreters'])

    # Paths for old entry
    old_script_dir = os.path.join(app.custom_config['workspace'], f"{config['username']}/{config['oldName']}")
    old_crontab_file = os.path.join(app.custom_config['crontab'], f"{config['username']}_{config['oldName']}_generated".lower())
    old_systemd_service = f"{config['username']}_{config['oldName']}_generated.service".lower()
    old_systemd_file = os.path.join(app.custom_config['systemd'], old_systemd_service)

    # Paths for new entry
    new_script_dir = os.path.join(app.custom_config['workspace'], f"{config['username']}/{config['name']}")
    new_crontab_file = os.path.join(app.custom_config['crontab'], f"{config['username']}_{config['name']}_generated".lower())
    new_systemd_service = f"{config['username']}_{config['name']}_generated.service".lower()
    new_systemd_file = os.path.join(app.custom_config['systemd'], new_systemd_service)

    # Path to .env directory
    env_dir = os.path.join(new_script_dir, '.env')

    # Remove/stop old crontab/systemd job
    if os.path.exists(old_crontab_file):
        os.remove(old_crontab_file)
    if os.path.exists(old_systemd_file):
        shell = Shell(working_directory=os.path.join(old_script_dir, ".env"))
        shell.run([
            ['systemctl', 'stop', old_systemd_service],
            ['systemctl', 'disable', old_systemd_service]
        ])
        os.remove(old_systemd_file)

    # Create shell
    shell = None
    if config['oldName'] != '' and config['oldName'] != config['name']:
        shutil.move(old_script_dir, new_script_dir)
        shell = Shell(working_directory=new_script_dir, env=config['environment'], log_dir=env_dir)
    else:
        create_dir_if_not_exist(new_script_dir)
        # Create dir for management files
        create_dir_if_not_exist(env_dir)
        # Change owner
        shell = Shell(working_directory=new_script_dir, env=config['environment'], log_dir=env_dir)
        shell.run([
            ['chown', '-R', f"{config['username']}:{config['username']}", new_script_dir],
            ['chown', '-R', "root:root", env_dir]
        ])

    # Remove unwanted files
    for f in config['filesToRemove']:
        if f == ".env":
            continue
        path = os.path.abspath(os.path.join(new_script_dir, f))
        if path.startswith(new_script_dir):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

    # Store uploaded files
    for f in config['files']:
        filepath = os.path.join(new_script_dir, f.filename)
        f.save(filepath)
        shell.run([['chown', '-R', f"{config['username']}:{config['username']}", filepath]])
    config['files'] = None

    # Create execution script
    with open(os.path.join(env_dir, 'execute.sh'), 'w') as f:
        output_file = os.path.join(new_script_dir, 'output.log')
        f.write("#!/bin/bash\n")
        f.write(f"cd {new_script_dir}\n")
        for e in config['environment']:
            f.write(f"export {e}={config['environment'][e]}\n")
        f.write('if [ "$1" == "service" ]; then\n')
        if config['interpreter']['name'] == "Native":
            f.write(f"{executable_path} {config['arguments']} {config['service-args']} >>{output_file} 2>&1\n")
        elif config['interpreter']['name'] == "System":
            f.write(f"{config['executable']} {config['arguments']} {config['service-args']} >>{output_file} 2>&1\n")
        else:
            f.write(f"{config['interpreter']['command']} {executable_path} {config['arguments']} {config['service-args']} >>{output_file} 2>&1\n")
        f.write('else\n')
        if config['interpreter']['name'] == "Native":
            f.write(f"{executable_path} {config['arguments']} >>{output_file} 2>&1\n")
        elif config['interpreter']['name'] == "System":
            f.write(f"{config['executable']} {config['arguments']} >>{output_file} 2>&1\n")
        else:
            f.write(f"{config['interpreter']['command']} {executable_path} {config['arguments']} >>{output_file} 2>&1\n")
        f.write('fi\n')
        f.flush()

    # Setup systemd service file and start it
    if config['scheduling'] == "systemd":
        with open(new_systemd_file, 'w') as f:
            for entry in SYSTEMD_CONFIG:
                if entry == "none":
                    continue
                f.write(f"[{entry}]\n")
                if entry == "Service":
                    f.write(f"User={config['username']}\n")
                    for env in config['environment']:
                        f.write(f"Environment=\"{env}={config['environment'][env]}\"\n")
                    if config['interpreter']['name'] == "Native":
                        f.write(f"ExecStart={executable_path} {config['arguments']} {config['service-args']}\n")
                    else:
                        f.write(f"ExecStart={config['interpreter']['command']} {executable_path} {config['arguments']} {config['service-args']}\n")
                for value in SYSTEMD_CONFIG[entry]:
                    if value["name"] == "WorkingDirectory":
                        working_dir = os.path.abspath(os.path.join(workspace, config['name'], config['systemd'][entry]['workingdirectory']))
                        f.write(f"WorkingDirectory={working_dir}\n")
                    else:
                        write_if(f, value["name"], config['systemd'][entry])
                f.write('\n')
            f.flush()

        shell.run([
            ['systemctl', 'enable', new_systemd_service],
        ])
        if config["systemd"]["none"]["initialstate"] == "started":
            shell.run([
                ['systemctl', 'start', new_systemd_service],
            ])

    # Setup crontab entry
    elif config['scheduling'] == 'crontab':
        crontab_line = f"{config['crontab']['minute']} {config['crontab']['hour']} {config['crontab']['day']} {config['crontab']['month']} {config['crontab']['weekday']} {config['username']} bash {env_dir}/execute.sh service\n"
        env_crontab = os.path.join(env_dir, f"{config['username']}_{config['name']}_generated".lower())
        with open(env_crontab, 'w') as f:
            f.write(f"# Managed by Script Dashboard\n{crontab_line}")
        shutil.copy2(env_crontab, new_crontab_file)

    # Create install script
    with open(os.path.join(env_dir, 'install.sh'), 'w') as f:
        f.write(config['install'].replace('\r', ''))

    install_content = config['install']
    # Store configuration
    with open(os.path.join(env_dir, 'config.yml'), 'w') as f:
        config['oldName'] = config['name']
        config['install'] = None
        yaml.dump(config, f)

    scripts = list_dir(workspace)

    try:
        # Execute install script
        ret = shell.run([
            ['sudo', '-u', config["username"], '/usr/bin/bash', os.path.join(env_dir, 'install.sh')]
        ])
        if ret != 0:
            config['error'] = 'Custom installation failed. Please check the input for e.g. syntax errors.'
            config['install'] = install_content
            config['files'] = list_files(new_script_dir)
            return render_template('script.html', username=current_user.id, config=config, systemd=SYSTEMD_CONFIG, scripts=scripts, interpreters=app.custom_config['interpreters'])
    except subprocess.TimeoutExpired:
        config['error'] = 'Configuration updated but custom installation failed because timeout occurred. Execution limit is 5 seconds.'
        config['install'] = install_content
        config['files'] = list_files(new_script_dir)
        return render_template('script.html', username=current_user.id, config=config, systemd=SYSTEMD_CONFIG, scripts=scripts, interpreters=app.custom_config['interpreters'])

    config['files'] = list_files(new_script_dir)
    return render_template('script.html', username=current_user.id, config=config, systemd=SYSTEMD_CONFIG, scripts=scripts, interpreters=app.custom_config['interpreters'])
