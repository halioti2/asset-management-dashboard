# Feature Planner

## MoSCoW Prioritization

### Must Have
- [x] Asset sync from Google Sheets
  - [x] Poll for changes every 3 minutes
  - [x] Write updates to local SQLite DB
- Asset list view
  - [x] Display all assets with key fields
  - [x] Filter by label / assignment status
- [ ] MDM integration Prep
  - [X] Lock Button
  - [ ] Unlock Button
- [ ] MDM integration
  - [ ] MDM hookup to buttons
- [ ] Spreadsheet + DB migration category break into type + status
  - [ ] Spreadsheet
  - [ ] DB



### Should Have
- [ ] Dev/staging pipeline
  - [ ] Staging environment on Fly.io (separate app + sheet) so migrations and deploys can be validated before hitting prod
  - [ ] Migration runbook / deployment checklist so rollback steps are documented and don't require a full git reset + new spreadsheet
- [ ] Cleared Labels i.e. ready to assign
- [ ] align filters with buttons
- [ ] All historical macbook records categorized for easy sorting

### Could Have
- Export to CSV
- Email notifications on asset changes
- Dashboard with summary stats
  - Total assets, unassigned count, recently updated
  - Asset detail page
  - Edit fields inline
  - View change history
- User authentication
  - Login / logout
  - Role-based access (admin vs viewer)

### Won't Have (for now)
- Multi-tenant support
- Mobile app
- Real-time collaborative editing

---

## Kanban Board

| Backlog | In Progress | Done |
|---------|-------------|------|
| | | Asset sync from Google Sheets |
| | | Asset list view |
| | MDM integration| |
| Dashboard summary stats | | |
