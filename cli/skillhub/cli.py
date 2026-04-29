import click
from skillhub.commands.init import init
from skillhub.commands.list_cmd import list_cmd


@click.group()
def cli():
    pass


cli.add_command(init)
cli.add_command(list_cmd, name="list")
