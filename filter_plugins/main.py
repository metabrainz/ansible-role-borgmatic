from collections.abc import Mapping

try:
    # AnsibleFilterTypeError was added in 2.10
    from ansible.errors import AnsibleFilterTypeError
except ImportError:
    from ansible.errors import AnsibleFilterError
    AnsibleFilterTypeError = AnsibleFilterError

from ansible.plugins.filter.core import to_nice_yaml


def parse_borgmatic_repositories(repos):
    """
    Parses a list of repositories and converts them to a format used by Borgmatic.
    Input:
    [
        {
            "type": "remote",
            "host": "storage.acme.com",
            "inventory_host": "backup-server",
            "user": "borg",
            "path": "./backups/{fqdn}"
        },
        "/var/lib/backups",
    ]
    Output:
    [
        "ssh://borg@storage.acme.com/./backups/{fqdn}",
        "/var/lib/backups",
    ]
    :param repos: list of repositories
    :return: list of repositories suitable for use in Borgmatic
    """
    if not isinstance(repos, list):
        raise AnsibleFilterTypeError("expected a list, got %s instead" % type(repos))

    repositories = []

    for repo in repos:
        if isinstance(repo, str):
            repositories.append(repo)
            continue
        elif not isinstance(repo, Mapping):
            raise AnsibleFilterTypeError("expected a string or mapping, got %s instead" % type(repo))

        repo_type = repo.get("type", "local")
        repo_path = repo.get("path")

        if repo_path is None:
            raise AnsibleFilterTypeError("repository path is required")
        elif repo_type == "local":
            repositories.append(repo_path)
        elif repo_type == "remote":
            repo_user = repo.get("user")
            repo_host = repo.get("host", repo.get("inventory_host"))

            if repo_user is None:
                raise AnsibleFilterTypeError("repository user is required")
            elif repo_host is None:
                raise AnsibleFilterTypeError("repository host is required")

            repositories.append("ssh://%s@%s/%s" % (repo_user, repo_host, repo_path))
        else:
            raise AnsibleFilterTypeError("unrecognised repository type %s" % repo_type)

    return repositories


def render_borgmatic_config(config):
    if not isinstance(config, Mapping):
        raise AnsibleFilterTypeError(
            "render_borgmatic_repositories requires a dictionary, got %s instead" % type(config))

    new_config = {}

    for section, options in config.items():
        if not isinstance(options, Mapping):
            raise AnsibleFilterTypeError(
                "value for section %s should be a dictionary, got %s instead" % (section, type(options)))

        new_config[section] = {}
        for option, value in options.items():
            if value is None:
                continue
            elif section == "location" and option == "repositories":
                new_config[section][option] = parse_borgmatic_repositories(value)
            else:
                new_config[section][option] = value

    return new_config


class FilterModule(object):

    def filters(self):
        return {
            "render_borgmatic_config": render_borgmatic_config,
        }
