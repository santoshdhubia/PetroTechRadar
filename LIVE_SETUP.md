# Live Radar Setup

1. Upload the contents of this package into the root of the existing `PetroTechRadar` repository.
2. Commit from the GitHub web interface while logged into your account.
3. Open **Actions → Refresh PetroTechRadar → Run workflow** once.
4. Open **Settings → Pages** and set **Source** to **GitHub Actions**.
5. Run **Deploy PetroTechRadar Pages** if it does not deploy automatically.

The scheduled refresh runs every Sunday at **03:30 UTC / 09:00 IST**.

## Automated commit identity

The workflow uses:

- Name: `Santosh Dhubia`
- Email: `santoshdhubia@users.noreply.github.com`

If your GitHub account uses a different private no-reply email, replace the email in `.github/workflows/refresh-radar.yml` before enabling scheduled refreshes.
