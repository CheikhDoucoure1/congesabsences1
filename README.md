# Déploiement — PETROSEN Congés & Absences

Guide de déploiement sur un serveur **Ubuntu/Debian**, en configuration
classique **Gunicorn + Nginx + systemd**. Toutes les commandes sont à
exécuter sur le serveur, en SSH.

Remplacez partout :
- `petrosen.exemple.sn` par le nom de domaine réel de l'application
- `/opt/conges-absences` par le chemin où vous déployez le code
- `deploy` par l'utilisateur système dédié (créé à l'étape 1)

---

## 0. Avant de commencer

- Un serveur Ubuntu/Debian avec accès `sudo`, à jour (`sudo apt update && sudo apt upgrade`).
- Un nom de domaine (ou une IP) pointant vers le serveur, si l'app doit être accessible depuis l'extérieur.
- Les informations LDAP/AD si vous activez l'authentification Active Directory (voir §12) — sinon les comptes locaux suffisent.

---

## 1. Utilisateur système dédié

Ne jamais faire tourner l'application en `root`.

```bash
sudo adduser --system --group --home /opt/conges-absences deploy
sudo mkdir -p /opt/conges-absences
sudo chown deploy:deploy /opt/conges-absences
```

## 2. Paquets système

```bash
sudo apt install -y python3 python3-venv python3-pip git \
    libldap2-dev libsasl2-dev libssl-dev \
    postgresql postgresql-contrib libpq-dev \
    nginx
```

`libldap2-dev`/`libsasl2-dev`/`libssl-dev` sont nécessaires pour compiler
`python-ldap` (authentification Active Directory) — à sauter si LDAP n'est
pas utilisé, mais les garder ne coûte rien. `libpq-dev` est nécessaire pour
`psycopg` (driver PostgreSQL).

## 3. Base de données PostgreSQL

Créez le rôle applicatif et la base, avec un mot de passe généré :

```bash
sudo -u postgres psql <<'EOF'
CREATE ROLE conges_absences WITH LOGIN PASSWORD 'Caccesabs@202!';
CREATE DATABASE conges_absences OWNER conges_absences;
EOF
```

Remplacez `'change-moi'` par un mot de passe fort (ex :
`openssl rand -base64 24`), et reportez-le dans `.env` (`DB_PASSWORD`,
§6). Ce rôle n'a besoin d'aucun privilège superutilisateur ni `CREATEDB` —
c'est uniquement l'API `manage.py test` (en développement) qui en a besoin,
pas l'application en production.

Par défaut PostgreSQL sur Ubuntu écoute uniquement sur `localhost` via
Unix socket + `peer`/`md5` selon l'utilisateur — le réglage par défaut
convient si Django et PostgreSQL tournent sur la même machine (`DB_HOST=
localhost` dans `.env`). Si la base est sur un autre serveur, ouvrez
`postgresql.conf`/`pg_hba.conf` en conséquence et gardez la connexion en
réseau interne uniquement (jamais PostgreSQL exposé directement sur
Internet).

## 4. Récupérer le code

```bash
sudo -u deploy -H bash -c '
  cd /opt/conges-absences
  git clone ><url-de-votre-depot .
'
```

Si le code n'est pas dans un dépôt git accessible depuis le serveur,
transférez-le avec `rsync` ou `scp` à la place :

```bash
rsync -avz --exclude .venv --exclude __pycache__ \
  ./ deploy@votre-serveur:/opt/conges-absences/
```

## 5. Environnement Python

```bash
sudo -u deploy -H bash -c '
  cd /opt/conges-absences
  python3 -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
  pip install gunicorn
'
```

## 6. Configuration (`.env`)

```bash
sudo -u deploy cp /opt/conges-absences/.env.example /opt/conges-absences/.env
sudo -u deploy nano /opt/conges-absences/.env
```

Valeurs **obligatoires** à définir pour la production :

```ini
# Générer avec :
#   .venv/bin/python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
DJANGO_SECRET_KEY=<une-valeur-longue-et-aleatoire>

DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=petrosen.exemple.sn
DJANGO_BEHIND_HTTPS=True

# Le rôle/mot de passe créés au §3
DB_NAME=conges_absences
DB_USER=conges_absences
DB_PASSWORD=<le-mot-de-passe-choisi-au-3>
DB_HOST=localhost
DB_PORT=5432
```

`DJANGO_BEHIND_HTTPS=True` n'a de sens qu'une fois HTTPS effectivement en
place (§10) — sinon Nginx et le navigateur se renverront la balle en boucle
de redirection. Le laisser à `False` tant que le certificat n'est pas posé.

Si vous activez LDAP/Active Directory, voir la section dédiée (§12) —
sinon laissez `DJANGO_LDAP_ENABLED=False`.

⚠️ `.env` contient des secrets (clé Django, mot de passe PostgreSQL, mot de
passe du compte LDAP) : vérifiez ses permissions (`chmod 600 .env`) et ne
le faites jamais transiter par git.

```bash
sudo chmod 600 /opt/conges-absences/.env
```

## 7. Base de données

```bash
sudo -u deploy -H bash -c '
  cd /opt/conges-absences
  source .venv/bin/activate
  python manage.py migrate
'
```

Pour un premier déploiement avec des données de démonstration (comptes de
test, à **ne pas utiliser en production réelle** — voir l'avertissement
affiché par la commande) :

```bash
sudo -u deploy -H bash -c '
  cd /opt/conges-absences && source .venv/bin/activate
  python manage.py init_data
'
```

Pour un vrai déploiement, créez plutôt un compte administrateur dédié :

```bash
sudo -u deploy -H bash -c '
  cd /opt/conges-absences && source .venv/bin/activate
  python manage.py shell -c "
from conges.models import Employe
from django.utils.crypto import get_random_string
mdp = get_random_string(16)
u = Employe.objects.create_user(username=\"admin\", email=\"admin@petrosen.sn\", password='Mdepass@8787', first_name=\"Admin\", last_name=\"Système\")
u.role = \"admin\"; u.actif = True; u.save()
print(\"Mot de passe admin genere :\", mdp)
"
'
```

Notez le mot de passe affiché — il ne sera plus jamais montré. Puis
importez les employés réels via `/administration/` (import Excel) une fois
connecté.

## 8. Fichiers statiques et médias

```bash
sudo -u deploy -H bash -c '
  cd /opt/conges-absences && source .venv/bin/activate
  python manage.py collectstatic --noinput
'
sudo mkdir -p /opt/conges-absences/media/avatars /opt/conges-absences/media/justificatifs
sudo chown -R deploy:deploy /opt/conges-absences/media
```

## 9. Gunicorn (service systemd)

Créez `/etc/systemd/system/conges-absences.service` :

```ini
[Unit]
Description=Gunicorn - PETROSEN Conges & Absences
After=network.target

[Service]
User=deploy
Group=deploy
WorkingDirectory=/opt/conges-absences
EnvironmentFile=/opt/conges-absences/.env
ExecStart=/opt/conges-absences/.venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/opt/conges-absences/gunicorn.sock \
    --access-logfile - \
    --error-logfile - \
    conges_absences.wsgi:application
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

`EnvironmentFile=.env` fonctionne seulement si `.env` ne contient **que**
des lignes `CLE=valeur` sans espaces autour du `=` et sans guillemets
autour des valeurs contenant des caractères spéciaux — c'est déjà le format
utilisé par `.env.example`.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now conges-absences
sudo systemctl status conges-absences
```

En cas de souci, les logs sont dans `journalctl` :

```bash
sudo journalctl -u conges-absences -f
```

## 10. Nginx (reverse proxy)

Créez `/etc/nginx/sites-available/conges-absences` :

```nginx
server {
    listen 80;
    server_name petrosen.exemple.sn;

    client_max_body_size 12M;  # un peu au-dessus de DATA_UPLOAD_MAX_MEMORY_SIZE (10 Mo)

    location /static/ {
        alias /opt/conges-absences/staticfiles/;
    }

    # Uniquement les avatars : peu sensibles, servis directement par Nginx.
    # Les justificatifs (documents médicaux, etc.) NE DOIVENT PAS être ici —
    # ils passent par Django (/mes-demandes/<id>/justificatif/), qui vérifie
    # que la personne a le droit de les voir avant de les servir.
    location /media/avatars/ {
        alias /opt/conges-absences/media/avatars/;
    }

    location / {
        proxy_pass http://unix:/opt/conges-absences/gunicorn.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/conges-absences /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

À ce stade, l'application est accessible en **HTTP** sur le port 80 —
passez tout de suite à HTTPS avant d'y mettre de vraies données.

### HTTPS avec Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d petrosen.exemple.sn
```

Certbot modifie automatiquement le bloc Nginx ci-dessus pour écouter en
443/TLS et rediriger le port 80. Une fois HTTPS confirmé fonctionnel,
repassez dans `.env` :

```ini
DJANGO_BEHIND_HTTPS=True
```

```bash
sudo systemctl restart conges-absences
```

Le renouvellement du certificat est automatique (timer systemd installé
par certbot) ; vérifiez-le une fois avec :

```bash
sudo certbot renew --dry-run
```

## 11. Pare-feu

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

## 12. LDAP / Active Directory (optionnel)

Si vous activez l'authentification AD (voir l'échange précédent pour le
détail des variables), dans `.env` :

```ini
DJANGO_LDAP_ENABLED=True
DJANGO_LDAP_SERVER_URI=ldap://PETROSEN-SRV-DC1.PETROSEN.SN:389
DJANGO_LDAP_BASE_DN=DC=PETROSEN,DC=SN
DJANGO_LDAP_BIND_DN=adminclb@petrosen.sn
DJANGO_LDAP_BIND_PASSWORD=<mot-de-passe-reel-du-compte-de-service>
```

⚠️ **`DJANGO_LDAP_BIND_DN` : toujours la forme `utilisateur@domaine`, jamais
`DOMAINE\utilisateur`.** Ça nous a coûté plusieurs jours de diagnostic en
production : le service systemd charge `.env` via `EnvironmentFile=`, qui
applique un échappement façon C aux valeurs — `\a` y devient un caractère
de contrôle invisible au lieu de rester un antislash littéral. Résultat :
`PETROSEN\adminclb` devenait silencieusement `PETROSENadminclb` (avec un
caractère invisible au milieu) au démarrage réel du service, alors que la
même valeur semblait parfaitement correcte partout où on la vérifiait — le
fichier `.env` lui-même, ou un `manage.py shell` lancé à la main (ce
dernier ne passe pas par `EnvironmentFile=`, donc ne montre jamais le
problème). La seule façon de le voir était d'inspecter l'environnement du
processus Gunicorn réellement en cours : `cat /proc/<pid du worker>/environ
| tr '\0' '\n' | grep DJANGO_LDAP`. La forme `utilisateur@domaine` évite
le problème puisqu'elle ne contient aucun caractère à échapper.

⚠️ **LDAP en clair, pas LDAPS.** Le contrôleur de domaine `PETROSEN-SRV-DC1`
n'expose pas le port 636 (confirmé après plusieurs tests réseau et
`ldapsearch` en diagnostic réel) — seul le 389 en clair répond. Les mots de
passe transitent donc non chiffrés sur ce trajet réseau. Si votre IT
confirme un jour que le contrôleur de domaine supporte **STARTTLS** sur ce
même port 389 (à vérifier avec `ldapsearch -ZZ ...` ou directement avec
eux), activez :

```ini
DJANGO_LDAP_START_TLS=True
```

et testez dans une fenêtre de maintenance — un DC qui ne le supporte pas
ferait à nouveau échouer toutes les connexions.

Vérifiez que le serveur peut atteindre le contrôleur de domaine sur le bon
port avant de redémarrer le service :

```bash
sudo -u deploy nc -zv PETROSEN-SRV-DC1.PETROSEN.SN 389
sudo systemctl restart conges-absences
```

Testez ensuite une connexion avec un compte AD réel depuis la page de
connexion de l'application.

### Vérifier que ça marche vraiment (du plus simple au plus précis)

Si la connexion échoue, remontez cette liste dans l'ordre — chaque étape
isole une cause différente sans dépendre des précédentes.

**1. Le réseau.** Le serveur joint-il le contrôleur de domaine sur le bon
port ? (389 en clair chez PETROSEN — testez le vôtre en premier avant de
supposer que c'est le même cas.)

```bash
sudo -u deploy nc -zv PETROSEN-SRV-DC1.PETROSEN.SN 389
```

Si ça échoue : pare-feu, DNS, ou le serveur n'est simplement pas sur le
même réseau que l'AD. Rien côté application ne peut compenser ça.

**2. Si vous testez LDAPS (636) ou STARTTLS, le certificat TLS.** La
poignée de main aboutit-elle ?

```bash
openssl s_client -connect PETROSEN-SRV-DC1.PETROSEN.SN:636 -showcerts </dev/null
# ou, pour STARTTLS sur le port 389 :
openssl s_client -starttls ldap -connect PETROSEN-SRV-DC1.PETROSEN.SN:389 -showcerts </dev/null
```

Cherchez `Verify return code: 0 (ok)` à la fin. Une erreur de certificat ici
(autorité inconnue, nom ne correspondant pas) confirme que vous avez besoin
de la variable `DJANGO_LDAP_CA_CERT_FILE` vue plus haut — jamais de contournement en
désactivant la validation. **Étape à sauter si vous êtes en LDAP simple
(389, sans STARTTLS) comme la config par défaut ci-dessus** — il n'y a pas
de TLS à négocier dans ce cas.

**3. Le bind et la recherche, indépendamment de Django.** Isole si le
problème vient du compte de service / de la base de recherche / du filtre,
avant même de faire intervenir l'application — **utilisez le même port et
protocole que `DJANGO_LDAP_SERVER_URI` dans votre `.env`**, pas un autre :

```bash
sudo apt install -y ldap-utils   # ldapsearch — outil de diagnostic uniquement
ldapsearch -H ldap://PETROSEN-SRV-DC1.PETROSEN.SN:389 \
  -D 'adminclb@petrosen.sn' -W \
  -b 'DC=PETROSEN,DC=SN' \
  '(sAMAccountName=<login-dun-vrai-compte-de-test>)'
```

`-W` demande le mot de passe du compte de service de façon interactive
(ne le mettez jamais en argument de commande, ça resterait dans
l'historique du shell). Si ça retourne bien l'entrée de l'utilisateur avec
ses attributs (`givenName`, `sn`, `mail`...), le service AD et le compte de
service fonctionnent — un souci restant serait forcément côté configuration
Django.

**4. Ce que le service réellement en cours utilise — pas ce que le fichier
`.env` ou un `manage.py shell` manuel montrent.** Un `.env` qui a l'air
correct, ou un test via `manage.py shell` lancé à la main, peuvent tous les
deux mentir : ni l'un ni l'autre ne passe par `EnvironmentFile=` de
systemd, qui applique un échappement façon C aux valeurs (voir
l'avertissement plus haut sur `DJANGO_LDAP_BIND_DN`). Seule l'inspection
du processus Gunicorn réellement démarré révèle une éventuelle
corruption :

```bash
sudo cat /proc/$(pgrep -f "gunicorn.*conges_absences.wsgi" | head -1)/environ | tr '\0' '\n' | grep DJANGO_LDAP
```

Comparez chaque valeur affichée à ce qu'il y a dans `.env`. Toute
différence (caractère manquant, invisible, ou différent) confirme une
corruption au chargement — évitez les antislashs dans les valeurs de
`.env` en général, pas seulement pour `DJANGO_LDAP_BIND_DN`.

**5. Django lui-même, avec les logs détaillés.** Activez temporairement le
log verbeux (voir `.env.example`) :

```ini
DJANGO_LDAP_DEBUG=True
```

```bash
sudo systemctl restart conges-absences
sudo journalctl -u conges-absences -f
```

Puis, dans un autre terminal, testez une authentification directement :

```bash
sudo -u deploy -H bash -c '
  cd /opt/conges-absences && source .venv/bin/activate
  python manage.py shell -c "
from django.contrib.auth import authenticate
u = authenticate(username=\"<login-ou-email-dun-vrai-compte-de-test>\", password=\"<son-mot-de-passe>\")
print(\"Résultat :\", u)
if u:
    print(\"role:\", u.role, \"| email:\", u.email, \"| actif:\", u.actif)
"
'
```

Le terminal avec `journalctl` affiche en direct chaque étape que
`django-auth-ldap` effectue (connexion, recherche, bind, récupération des
attributs) — c'est ici que vous verrez la raison précise d'un échec silencieux.
**Repassez `DJANGO_LDAP_DEBUG=False` une fois le diagnostic terminé** : en
mode debug, les tentatives de connexion sont journalisées en détail, ce
qu'on ne veut pas laisser tourner en continu en production.

**6. Bout en bout.** Connectez-vous avec un vrai compte AD depuis la page
de connexion de l'application, puis vérifiez dans `/administration/` que
le compte est bien apparu (voir l'échange précédent : il est créé
automatiquement au premier login réussi, avec le rôle par défaut — à
compléter ensuite via l'écran "Modifier l'employé").

## 13. Sauvegardes

Deux choses à sauvegarder régulièrement : la base **PostgreSQL** et le
dossier **médias** (justificatifs, avatars).

```bash
sudo mkdir -p /opt/backups
sudo chown deploy:deploy /opt/backups
```

Exemple de sauvegarde quotidienne via cron (`sudo -u deploy crontab -e`) :

```cron
0 2 * * * PGPASSWORD='<le-mot-de-passe-du-2>' pg_dump -h localhost -U conges_absences -Fc conges_absences > /opt/backups/conges-db-$(date +\%Y\%m\%d).dump
5 2 * * * tar -czf /opt/backups/conges-media-$(date +\%Y\%m\%d).tar.gz -C /opt/conges-absences media
15 2 * * * find /opt/backups -type f -mtime +30 -delete
```

`pg_dump -Fc` produit un format compressé/custom, à restaurer avec
`pg_restore` :

```bash
pg_restore -h localhost -U conges_absences -d conges_absences --clean --if-exists /opt/backups/conges-db-XXXXXXXX.dump
```

Pensez à faire tourner ces archives ailleurs que sur le même disque (autre
machine, stockage objet...), et à **tester une restauration au moins une
fois** — une sauvegarde jamais restaurée n'est qu'une hypothèse.

## 14. Mise à jour de l'application

```bash
sudo -u deploy -H bash -c '
  cd /opt/conges-absences
  git pull
  source .venv/bin/activate
  pip install -r requirements.txt
  python manage.py migrate
  python manage.py collectstatic --noinput
'
sudo systemctl restart conges-absences
```

---

## Checklist avant mise en production réelle

- [ ] `DJANGO_DEBUG=False`
- [ ] `DJANGO_SECRET_KEY` défini avec une vraie valeur aléatoire (pas celle de `.env.example`)
- [ ] `DJANGO_ALLOWED_HOSTS` limité au(x) vrai(s) nom(s) de domaine
- [ ] HTTPS actif et `DJANGO_BEHIND_HTTPS=True`
- [ ] `.env` en permissions `600`, jamais commité
- [ ] `DB_PASSWORD` défini avec une vraie valeur (pas celle de `.env.example`), rôle PostgreSQL sans `CREATEDB`/superutilisateur
- [ ] Comptes de démonstration (`init_data`) **supprimés ou désactivés** si utilisés pour les premiers tests — sinon `admin@petrosen.sn / admin123` reste un compte admin valide en production
- [ ] Sauvegardes automatiques en place, **restauration testée au moins une fois** (`pg_restore`)
- [ ] Pare-feu actif, seuls SSH/80/443 ouverts (PostgreSQL jamais exposé publiquement)
