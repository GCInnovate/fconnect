from fabric.api import local, abort, run, lcd, cd, settings, sudo, env

env.hosts = ['llinweb']
env.use_ssh_config = True


def deploy():
    local_code_dir = '/Users/sam/projects/mtrackpro'
    with lcd(local_code_dir):
        local("git push origin master")
    code_dir = '/var/www/mtrackpro/web'
    with cd(code_dir):
        run("git pull origin master")
        sudo("supervisorctl restart mtrackpro")
