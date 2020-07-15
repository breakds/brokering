import subprocess
import logging


logger = logging.getLogger('auth')


class PasswordFetcher(object):
    """A PasswordFetcher is an interface whose implementer implements an
    API FetchPassword() to generate a password to use.

    The API FetchPassword returns a string representing the password.

    """

    def FetchPassword():
        return 'NOPASSWORD'


class PlainPasswordFetcher(object):
    """Return a password passed in as plain text.

    NOTE that this is not recommended for practical use due to
    security concerns, since you will have to expose your plaintext
    password somewhere in the code or configuration.

    """

    def __init__(self, plaintext_password):
        self.password = plaintext_password

    def FetchPassword(self):
        return self.password


class PassStoreFetcher(PasswordFetcher):
    """A PasswordFetcher implementation that prompts and return the
    corresponding password from pass store.

    See https://www.passwordstore.org/ for details.

    """

    def __init__(self, entry_name=None):
        self.entry_name = entry_name


    def FetchPassword(self):
        """Returns the password fetched from the pass store.

        NOTE that this fucntion may require console input from the
        user, and therefore is only advised to use in CLI programs.

        This function throws when the command subprocess fails, due to
        the reasons e.g. pass is not installed.

        """

        cmd = ['pass', self.entry_name]
        completed_proc = subprocess.run(cmd, capture_output=True)
        if completed_proc.returncode != 0:
            raise RuntimeError('Invalid Pass Store Invokation - {}'.format(
                completed_proc.stderr.decode('ascii')))
        return completed_proc.stdout.decode('ascii').strip()


__all__ = ['PasswordFetcher', 'PlainPasswordfetcher', 'PassStorefetcher']


if __name__ == '__main__':
    # If the user execute this file by itself, the code below will run
    # to perform some manual testing
    pwd_fetcher = PassStoreFetcher('mail.breakds.org/bds')
    print(pwd_fetcher.FetchPassword())
