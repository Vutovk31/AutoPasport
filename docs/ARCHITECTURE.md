# Architecture

## Repository integrity boundary

```text
push / pull request
→ checkout
→ verify required project artifacts
→ verify VERSION ↔ README
→ continue to migrations, compile and tests
```

Релиз не считается проверяемым, если отсутствует хотя бы один обязательный компонент приложения. Integrity workflow является первым release-gate перед функциональными тестами.
