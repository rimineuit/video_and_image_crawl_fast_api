import re
import os
import click
import json

from loguru import logger
# HEHE

from .tiktokcomment import TiktokComment
from .tiktokcomment.typing import Comments

__title__ = 'TikTok Comment Scrapper'
__version__ = '2.0.0'
__MINH__ = '1.0.0'
def get_comments(
    aweme_id: str,
): 
    if(not aweme_id):
        raise ValueError('example id : 7418294751977327878')      
    
    logger.info(
        'start scrap comments %s' % aweme_id
    )

    comments: Comments = TiktokComment()(
        aweme_id=aweme_id
    )
    
    return comments.dict

# import sys
# if(__name__ == '__main__'):
#     id = sys.argv[1] if len(sys.argv) > 1 else "7418294751977327878"
#     print(get_comments(aweme_id=id))