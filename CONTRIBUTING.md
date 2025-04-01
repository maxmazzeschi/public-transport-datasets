## Contributing to public-transport-datasets

Thank you for your interest in contributing to `public-transport-datasets`! 
We welcome contributions of all kinds, including bug fixes, new features, documentation improvements, and tests.

### Getting Started

1. **Fork the Repository**:
   Click the "Fork" button on GitHub and clone your fork locally:
   ```sh
   git clone https://github.com/maxmazzeschi/public-transport-datasets
   cd public-transport-datasets
   ```

2. **Set Up the Environment**:
   We recommend using a virtual environment:
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Run Tests**:
   Before making changes, ensure everything is working:
   ```sh
   pytest
   ```

---

## How to Contribute

### 1. Reporting Issues
- Check if the issue already exists in [Issues](https://github.com/maxmazzeschi/public-transport-datasets/issues).
- If not, create a **new issue**, providing:
  - A clear description of the bug or feature request.
  - Steps to reproduce the bug (if applicable).
  - The expected and actual behavior.

### 2. Submitting a Pull Request (PR)
1. Create a new branch for your fix or feature:
   ```sh
   git checkout -b feature-new-functionality
   ```
2. Make your changes and **ensure tests pass**.
3. Format the code using [Black](https://black.readthedocs.io/):
   ```sh
   black .
   ```
4. Run `flake8` for linting:
   ```sh
   flake8 .
   ```
5. Commit changes with a meaningful message:
   ```sh
   git commit -m "Add support for XYZ in public-transport-datasets"
   git push origin feature-new-functionality
   ```
6. Open a **Pull Request (PR)**:
   - Go to [Pull Requests](https://github.com/maxmazzeschi/public-transport-datasets/pulls) and click "New PR".
   - Add a clear title and description of your changes.
   - Link to any related issues using `Fixes #issue-number`.
   - Wait for a review and respond to feedback.

---

## Coding Guidelines
- Follow [PEP 8](https://peps.python.org/pep-0008/) for Python code style.
- Use type hints where possible (`def load_dataset(path: str) -> Dataset:`).
- Write **docstrings** using [PEP 257](https://peps.python.org/pep-0257/).
- Keep functions small and modular.

---

## Testing
We use `pytest` for testing. Before submitting, ensure:
```sh
pytest --cov=public-transport-datasets
```
- New features should include corresponding tests.
- Test files are in the `tests/` folder.

---

## Need Help?
- Open an issue if you're stuck.
- Send an email to [Max](mailto:max.mazzeschi@gmail.com)

**Happy coding! 🎉**

