-- Comptes fournis pour l'épreuve. À exécuter APRÈS sql/schema.sql.
-- Mot de passe des deux comptes : Formation2026!
-- Hachages bcrypt ($2b$, 12 tours) générés avec le paquet Python bcrypt.
--
-- Régénération (dans le venv du projet) :
--   python -c "import bcrypt; print(bcrypt.hashpw(b'Formation2026!', \
--     bcrypt.gensalt(rounds=12)).decode())"
-- Vérification :
--   python -c "import bcrypt; print(bcrypt.checkpw(b'Formation2026!', \
--     b'<hachage>'))"

INSERT INTO utilisateur (username, mot_de_passe_hash, role) VALUES
  ('exploitant01',
   '$2b$12$ej20gmOU7l.L1SOku8K66uV2PMETEc5ub8A.PM.Y.7QGHEvUlBkEi',
   'exploitant'),
  ('direction01',
   '$2b$12$l8m1OACxjxS8rOcvTBH7oOuxkXEfMed1KAcZIZDxGZPLvBmR4w8We',
   'direction')
ON CONFLICT (username) DO UPDATE
  SET mot_de_passe_hash = EXCLUDED.mot_de_passe_hash,
      role = EXCLUDED.role;
