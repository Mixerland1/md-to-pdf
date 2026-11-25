# 0.4.0 beta 9 — save confirmation

Replace the negative close prompt with “Сохранить изменения?” and three explicit actions: Save, Don't save, Cancel. Escape and closing the dialog cancel the operation. Save must succeed before closing, opening another document, replacing clipboard text or restarting for an update. Cancelled filename selection and save errors keep the current document open. Clean documents close without asking. Saving persists the editable project, not the exported PDF.

Includes beta 8 metadata roles and table controls. Manual desktop verification pending.