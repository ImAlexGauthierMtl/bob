---
name: dx_base_create_alembic_convert_sql_file
description: Convertit un fichier SQL artisanal (init.sql, seed.sql, schema.sql) en révision Alembic avec upgrade + downgrade.
metadata:
  reference: § 2.7.5
---

# dx_base_create_alembic_convert_sql_file

## Actions
Pour chaque fichier `.sql` trouvé hors d'Alembic :
1. Lire le contenu, regrouper par opération atomique
2. Pour chaque `CREATE`, générer un `op.create_X` ou `op.execute("CREATE ...")` dans `upgrade()`
3. Pour chaque opération, ajouter l'inverse dans `downgrade()`
4. Créer la révision : `alembic revision -m "import_<filename>"`
5. Supprimer le fichier SQL original
6. Vérifier avec `dx_base_check_alembic_no_manual_sql_files`
