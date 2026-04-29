import click
from skillhub.commands.init import init
from skillhub.commands.list_cmd import list_cmd
from skillhub.commands.pull import pull
from skillhub.commands.setup_cmd import setup
from skillhub.commands.build import build
from skillhub.commands.push import push


@click.group()
def cli():
    pass


cli.add_command(init)
cli.add_command(list_cmd, name="list")
cli.add_command(pull)
cli.add_command(setup)
cli.add_command(build)
cli.add_command(push)
