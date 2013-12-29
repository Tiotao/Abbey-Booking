#   ######   #######  ##    ##  ######  ########    ###    ##    ## ######## 
#  ##    ## ##     ## ###   ## ##    ##    ##      ## ##   ###   ##    ##    
#  ##       ##     ## ####  ## ##          ##     ##   ##  ####  ##    ##    
#  ##       ##     ## ## ## ##  ######     ##    ##     ## ## ## ##    ##    
#  ##       ##     ## ##  ####       ##    ##    ######### ##  ####    ##    
#  ##    ## ##     ## ##   ### ##    ##    ##    ##     ## ##   ###    ##    
#   ######   #######  ##    ##  ######     ##    ##     ## ##    ##    ##    


import os

# Server
PORT = int(os.environ.get('PORT', 3000))
HOST = '0.0.0.0'
SECRET_KEY = 
DEBUG = True

# Google Cal
APPROVED_CAL_ID = 
PENDING_CAL_ID = 
DEVELOPER_ID = 

# Google Spreadsheet
SPREADSHEET_ACC = 
SPREADSHEET_PW = 
SPREADSHEET_ID = 
PERMIT_ID = 
LOG_KEY = ['id','timestamp','name','matric','room','purpose','starttime','endtime','email','phone','people','status', 'approved_time']
PERMIT_VALIDATE = False
ADMIN_VALIDATE = True


# Mail
MAIL_SERVER = 
MAIL_PORT = 
MAIL_USE_TLS = 
MAIL_USE_SSL = 
MAIL_USERNAME = 
MAIL_PASSWORD = 

SERVICE_MAIL = 
ADMIN_MAIL = 
GROUP_MAIL = 