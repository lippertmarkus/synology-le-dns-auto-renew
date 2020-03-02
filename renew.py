import os
import subprocess
import sys

if len(sys.argv) < 3:
    sys.exit("Need exactly two arguments: renew.py *.example.com dns_doapi")

DOMAIN = sys.argv[1]
DNS = sys.argv[2]
DRY = False  # if set to true the script won't change anything but only shows what it would do


""" ################################# PATHS AND BINARIES ############################################# """

OPENSSL = "openssl"
CERTROOTDIR = "/usr/syno/etc/certificate"
PACKAGECERTROOTDIR = "/usr/local/etc/certificate"
FULLCERTDIR = CERTROOTDIR + "/_archive"
ACME = "/usr/local/share/acme.sh/acme.sh"

certDir = None


""" ################################# HELPER FUNCTIONS ############################################# """


def renew_cert(cert_directory):
    print("\n♦♦♦ RENEW CERT ♦♦♦")
    if not DRY:
        subprocess.run(['bash', ACME, '--renew', '--force', '-d', DOMAIN, '--dns', DNS], check=True)
        subprocess.run(['bash', ACME, '--install-cert', '--force', '-d', DOMAIN,
                        '--cert-file', os.path.join(cert_directory, 'cert.pem'),
                        '--key-file', os.path.join(cert_directory, 'privkey.pem'),
                        '--fullchain-file', os.path.join(cert_directory, 'fullchain.pem'),
                        '--capath', os.path.join(cert_directory, 'chain.pem')], check=True)


def certificate_has_correct_subject(certificate_filepath):
    subject = subprocess.run([OPENSSL, 'x509', '-in', certificate_filepath, '-subject', '-noout'],
                             stdout=subprocess.PIPE, check=True).stdout.decode('utf-8').strip()
    return subject.endswith(DOMAIN)


def copy_certs(source, target):
    # add trailing slashes
    source = os.path.join(source, '')
    target = os.path.join(target, '')

    print("\n🔧 Copying from {} to {}".format(source, target))
    if not DRY:
        subprocess.run(['rsync', '-avh', source, target])  # using rsync to keep permissions


def restart_app(app):
    print("\n🔧 Restarting " + app)
    if not DRY:
        subprocess.run(['/usr/syno/bin/synopkg', 'restart', app])


""" ################################# MAIN SCRIPT ############################################# """


# search main directory of the certificate we wan't to renew
for root, dirs, files in os.walk(FULLCERTDIR):
    for file in files:
        if file == 'cert.pem':
            currFile = os.path.join(root, file)

            if certificate_has_correct_subject(currFile):
                certDir = root
                break

# stop script if main certificate directory wasn't found
if certDir is None:
    sys.exit("Certificate for {} not found under {}".format(DOMAIN, FULLCERTDIR))
else:
    print("✔✔✔ Found cert for {} under {} ✔✔✔".format(DOMAIN, certDir))

# Renew the certificate and override the one in the previously found certificate directory
renew_cert(certDir)

# find system apps which are using the certificate and replace it with the renewed one
print("\n♦♦♦ WORKING ON SYSTEM APPS ♦♦♦")
for root, dirs, files in os.walk(CERTROOTDIR):
    for file in files:
        if (not root.startswith(FULLCERTDIR)) and (file == 'cert.pem'):  # find all not under _archive
            currFile = os.path.join(root, file)

            if certificate_has_correct_subject(currFile):
                copy_certs(certDir, root)

# reload nginx to make sure the renewed certificate is used
print("\n♦♦♦ RELOADING NGINX ♦♦♦")
if not DRY:
    subprocess.run(['/usr/syno/sbin/synoservicectl', '--reload', 'nginx'])

# find other apps which are using the certificate and replace it with the renewed one
print("\n♦♦♦ WORKING ON OTHER APPS ♦♦♦")
for root, dirs, files in os.walk(PACKAGECERTROOTDIR):
    for file in files:
        if file == 'cert.pem':
            currFile = os.path.join(root, file)

            if certificate_has_correct_subject(currFile):
                appName = os.path.basename(os.path.dirname(root))  # get app name by directory
                print("\n\n📀 " + appName)
                copy_certs(certDir, root)
                restart_app(appName)
