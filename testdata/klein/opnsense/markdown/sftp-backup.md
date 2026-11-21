# Backups via secure copy (sftp)

When your remote host supports SSH, it's often possible to use sftp as well, which can be used for file transfers in a secure manner between machines (in this case your firewall and the backup target).

In order to use this feature, one has to install the sftp-backup plugin first (in `System->Firmware->Plugins` search for os-sftp-backup).

## Preparation

Before configuring the plugin, make sure your target machine has ssh enabled and is reachable. You also need a private/public key combination which the backup machine will trust.

Generate a key with the command below (<span class="title-ref">-f</span> specifies the filename) and omit a password in the process:

```
ssh-keygen -t ed25519 -C "your_email@example.com" -f my_new_key
```

The output will look like this:

```
Generating public/private ed25519 key pair.
Enter passphrase (empty for no passphrase):
Enter same passphrase again:
Your identification has been saved in my_new_key
Your public key has been saved in my_new_key.pub
The key fingerprint is:
SHA256:DJ+Jj1xeuezYLYaqOQg9DBa8ETmOuausIf1rNKeuMQs your_email@example.com
The key's randomart image is:
+--[ED25519 256]--+
|..o              |
| *               |
|o.=   .          |
|++     = o .     |
|.=    . S o      |
|o.+ o..= o .     |
|Eo++ +o o.o      |
|+o.=+.  .+o.     |
|=.o+*+....o..    |
+----[SHA256]-----+
```

This creates two files, <span class="title-ref">my_new_key</span> and <span class="title-ref">my_new_key.pub</span>, the first one is private and should not be shared, the other is public and offered to the backup machine.

Next we will add the <span class="title-ref">my_new_key.pub</span> file to the <span class="title-ref">authorized_keys</span> file in the users <span class="title-ref">.ssh</span> directory (e.g. <span class="title-ref">/home/opnsense/.ssh/authorized_keys</span>).

> [!NOTE]
> Make sure the <span class="title-ref">.ssh</span> directory is only readable and writebable by the owner and <span class="title-ref">authorized_keys</span> has the same rights. (<span class="title-ref">chmod 600</span> for the file <span class="title-ref">chmod 700</span> for the directory)

> [!TIP]
> Create a separate key for the backup (don't use the same one elsewhere), so you can easily drop access later.

## Initial setup

The configuration part of this plugin is quite basic and offers two types of transport modes, https using a username and password combination or ssh using public key infrastructure.

------------------------------------------------------------------------

|  |  |
|----|----|
| Enable | Enable backup to the upstream target |
| URL | Target location, which defines protocol, user and path. This may look like: <span class="title-ref">sftp://opnsense@192.168.1.10//home/opnsense/config_backups</span> |
| SSH private key | Upload the <span class="title-ref">my_new_key</span> file created during preparation. |
| Backup Count | Number of backups to keep |
| Encrypt Password | Password used to encrypt the backup (optional) |

## Finish and test

After willing in the details, press "Setup/Test sftp" to validate if it works. When connectivity isn't possible, the error will be reported.

> [!TIP]
> For advanced debugging use <span class="title-ref">sftp</span> on the command line, this plugin uses the same tool and reports the same errors.
