"""Start/process local AWS APIs without an AWS account."""
import argparse
import os
import time
from backend.storage import init_db
from backend.platform_store import initialize
from backend import aws_services

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action',choices=['bootstrap','worker','index'])
    args = parser.parse_args()
    init_db();initialize()
    if args.action=='bootstrap':
        print(aws_services.bootstrap())
    elif args.action=='index':
        print(aws_services.index_evidence())
    else:
        print('Processing local SQS analysis jobs; Ctrl+C stops the worker.')
        while True:
            result = aws_services.consume_one()
            if result['processed']:
                print(result)
            time.sleep(1)
