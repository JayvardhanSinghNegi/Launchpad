import click
from devopsify.commands.run import run
from devopsify.utils.display import print_banner


@click.group()
def cli():
    pass


@cli.command()
@click.option("--cloud", is_flag=True, default=False, help="Deploy to AWS EKS instead of minikube.")
@click.option("--repo", default=None, help="GitHub repo URL (skip interactive prompt).")
def deploy(cloud, repo):
    """Clone a GitHub repo and generate + deploy a full DevOps setup around it."""
    print_banner()
    run(cloud=cloud, repo_url=repo)


def main():
    cli()


if __name__ == "__main__":
    main()
