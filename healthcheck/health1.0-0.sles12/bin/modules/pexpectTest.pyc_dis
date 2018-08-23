# Embedded file name: ./bin/modules/pexpectTest.py
import pexpect
username = 'admin'
ip = '10.41.0.9'
password = 'HP1nv3nt'
sshCmd = 'ssh -o PubkeyAuthentication=no -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no ' + username + '@' + ip
child = pexpect.spawn(ftpCmd, timeout=5)
child.expect('(?i)name.*:\\s*')
child.sendline(username)
child.expect('(?i)password:\\s*')
child.sendline(password)
child.expect('ftp>\\s*')
child.sendline('bin')
child.expect('ftp>\\s*')
child.sendline('throttle put 100000')
child.expect('ftp>\\s*')
cmd = 'put ' + imageFile
child.sendline(cmd)
child.expect('File successfully transferred.*ftp>\\s*')
child.sendline('quit')