"""营销报表专属配置；不读取千帆认证配置，不输出凭据。"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env', override=False)

# 来源：官方新兴趣报告 pageId=103892、地域 pageId=103889。同一只读接口。
REPORT_URL = 'https://api.baidu.com/json/sms/service/OpenApiReportService/getReportData'


class BaiduReportError(Exception):
    def __init__(self, code: str, message: str, status_code=502):
        super().__init__(message)
        self.code, self.message, self.status_code = code, message, status_code


@dataclass(repr=False)
class BaiduReportSettings:
    access_token: str = field(default_factory=lambda: os.getenv('BAIDU_MARKETING_ACCESS_TOKEN', '').strip())
    user_name: str = field(default_factory=lambda: os.getenv('BAIDU_MARKETING_USER_NAME', '').strip())
    timeout: float = 30
    amount_unit: str = 'unknown'
    ctr_unit: str = 'unknown'

    def require_credentials(self):
        if not self.access_token or not self.user_name:
            raise BaiduReportError('baidu_not_configured', '待真实联调：请在后端配置 BAIDU_MARKETING_ACCESS_TOKEN 和 BAIDU_MARKETING_USER_NAME，然后重启后端。', 503)


def get_baidu_settings() -> BaiduReportSettings:
    try:
        settings = BaiduReportSettings(
            timeout=float(os.getenv('BAIDU_MARKETING_TIMEOUT_SECONDS', '30')),
            amount_unit=os.getenv('BAIDU_MARKETING_AMOUNT_UNIT', 'unknown'),
            ctr_unit=os.getenv('BAIDU_MARKETING_CTR_UNIT', 'unknown'),
        )
        if not 1 <= settings.timeout <= 60 or settings.amount_unit not in ('unknown', 'yuan', 'fen') or settings.ctr_unit not in ('unknown', 'ratio', 'percent'):
            raise ValueError
        return settings
    except ValueError:
        raise BaiduReportError('baidu_configuration_invalid', '百度营销配置不合法：检查超时（1–60秒）及金额、CTR单位枚举。', 503) from None
