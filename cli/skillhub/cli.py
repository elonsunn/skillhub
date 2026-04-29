import click
from skillhub.commands.init import init


@click.group()
def cli():
    pass


cli.add_command(init)
