# CDI Profile Collection

## Running Pre-Commit

1. Set up development environment:

```bash
   pixi shell -e dev
   pixi run pre-commit-install
```

2. Run pre-commit on all files:

```bash
   pixi run pre-commit-run
```

3. Individual tool usage:

```bash
    pixi run lint
    pixi run format
    pixi lint-fix
    pixi run black-format
    pixi run isort-fix
```

4. Update pre-commit hooks:

```bash
   pixi run pre-commit-update
```
