
tapdc.tgz: www/* fb.py ssi.js
	tar cvzf tapdc.tgz www/* fb.py ssi.js

put:
	scp -i ../ssh/private-openssh-format tapdc.tgz root@104.236.50.117:tapdc.tgz
	
	
