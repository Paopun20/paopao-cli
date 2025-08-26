try:
    import git
except ImportError:
    raise ImportError("GitPython is required for git operations. Please install it via 'pip install GitPython'.")

def download_branch(repo_url, branch, dest):
    try:
        git.Repo.clone_from(repo_url, dest, branch=branch)
    except Exception as e:
        raise RuntimeError(f"Failed to clone repository: {e}")

def get_latest_commit(repo_path):
    try:
        repo = git.Repo(repo_path)
        return repo.head.commit.hexsha
    except Exception as e:
        raise RuntimeError(f"Failed to get latest commit: {e}")