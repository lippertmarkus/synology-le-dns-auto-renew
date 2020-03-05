# Automatically renew Let's Encrypt certificate on Synology NAS using DNS-01 challenge
Python script for automatically renewing Let's Encrypt certificates on Synology NAS using DNS-01 challenge. Also supports wildcard certificates.

More sophisticated way of the [bash script in the acme.sh wiki](https://github.com/acmesh-official/acme.sh/wiki/Synology-NAS-Guide#configuring-certificate-renewal) (which helped me a lot!) with the following features/improvements:
- Automatically finds the main certificate folder under `/usr/syno/etc/certificate/_archive/`
- Only replaces certificates with the correct domain name in the certificate subject instead of replacing all certificates of all apps. Using `openssl` already installed on Synology NAS for finding out certificate subject name.
- Supports environments using multiple certificates as well as Synology Directory Server without causing problems
- Uses `rsync` to keep permissions like they should be
- Automatically restarts nginx for DSM, Reverse Proxy and other system apps as well as normal applications as needed

## Background
- DSM on Synology NAS natively only supports issuing and renewing [certificates via HTTP-01](https://www.synology.com/en-us/knowledgebase/DSM/help/DSM/AdminCenter/connection_certificate), but not the DNS-01 challenge of Let's Encrypt. 
- If your NAS is not connected to the Internet, you don't want to open port 80 or you want to use wildcard certificates, you would need to use the [DNS-01 challenge of Let's Encrypt](https://letsencrypt.org/docs/challenge-types/).
- Although you can issue a certificate via the command line, import it via DSM and use it for the Synology apps, automatically renewing it is a bit tricky. Because every app has a seperate copy of the certificate you need to find all those locations and replace the certificate with the renewed one.

Various guides (e.g. [this one](https://vdr.one/how-to-create-a-lets-encrypt-wildcard-certificate-on-a-synology-nas/)) explain the manual way of importing and renewing the certificate. The only script to automate the renewal I found is described in the [wiki of acme.sh](https://github.com/acmesh-official/acme.sh/wiki/Synology-NAS-Guide#configuring-certificate-renewal). The provided bash script however has a few drawbacks in my opinion:
- You need to manually find the main certificate directory under `/usr/syno/etc/certificate/_archive/`. Although this is a one-time task, it can be time consuming if you have multiple certificates.
- It replaces all certificates of all apps with the renewed certificate. E.g. if you have an app `App1` using a cert for `example1.com` and another app `App2` using a cert for `example2.com` and then use the bash script to renew the cert for `example2.com` you'll end up with both apps now having the cert for `example2.com`.

## Usage

Detailed explanation will be available soon.

Short version:

1. Install `acme.sh` on your Synology NAS:
    ```bash
    sudo -i
    wget https://github.com/acmesh-official/acme.sh/archive/master.tar.gz
    tar xfv master.tar.gz
    cd acme.sh-master/
    ./acme.sh --install --nocron --home /usr/local/share/acme.sh --accountemail "me@example.com"  # ignore socat warning
    ```
2. Issue certificate like normally:
    ```bash
    cd /usr/local/share/acme.sh
    # set environment variables according to your used DNS API before issuing
    ./acme.sh --issue -d "*.example.com" --dns dns_doapi --force
    # ...
    # copy cert files for importing via DSM, e.g. to a share
    cp -R /usr/local/share/acme.sh/*.example.com/ /volume1/myshare/mycert/
    ```
3. Import certificate via DSM and configure apps to use it.
4. Install and test the script:
    ```bash
    mkdir /usr/local/share/le-renew
    wget -P /usr/local/share/le-renew/ https://raw.githubusercontent.com/lippertmarkus/synology-le-dns-auto-renew/master/renew.py
    python3 /usr/local/share/le-renew/renew.py *.example.com dns_doapi
    ```
    If you're cautios you can set `DRY = True` at the beginning of the script to do a dry run without applying any changes to any files and without really renewing the cert. The output shows which files would be overwritten.

5. Create a recurring task via DSM to run the script (don't directly set up a cronjob as the DSM security advisor will give you a warning).

## Example output

```
✔✔✔ Found cert for *.example.com under /usr/syno/etc/certificate/_archive/aBcDef ✔✔✔

RENEW CERT
[Tue Mar  3 18:53:06 CET 2020] Renew: '*.example.com'
# ...
[Tue Mar  3 18:53:14 CET 2020] Installing cert to:/usr/syno/etc/certificate/_archive/aBcDef/cert.pem
# ...

♦♦♦ WORKING ON SYSTEM APPS ♦♦♦

🔧 Copying from /usr/syno/etc/certificate/_archive/aBcDef/ to /usr/syno/etc/certificate/ReverseProxy/9f6f23dc-90a1-4e08-a99b-f9a4ffe96ca7/
sending incremental file list
cert.pem
chain.pem
fullchain.pem
privkey.pem

sent 9.09K bytes  received 88 bytes  18.35K bytes/sec
total size is 8.82K  speedup is 0.96


♦♦♦ RELOADING NGINX ♦♦♦
nginx reloaded.


♦♦♦ WORKING ON OTHER APPS ♦♦♦

📀 VPNCenter

🔧 Copying from /usr/syno/etc/certificate/_archive/aBcDef/ to /usr/local/etc/certificate/VPNCenter/OpenVPN/
sending incremental file list
cert.pem
chain.pem
fullchain.pem
privkey.pem

sent 9.09K bytes  received 88 bytes  6.12K bytes/sec
total size is 8.82K  speedup is 0.96

🔧 Restarting VPNCenter
package VPNCenter restart successfully
```
