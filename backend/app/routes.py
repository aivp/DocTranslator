from app.resources.admin.auth import AdminLoginResource, AdminChangePasswordResource
from app.resources.admin.customer import AdminCustomerListResource, AdminCreateCustomerResource, \
    AdminCustomerDetailResource, AdminUpdateCustomerResource, AdminDeleteCustomerResource, \
    CustomerStatusResource
from app.resources.admin.image import AdminImageResource
from app.resources.admin.settings import AdminSettingNoticeResource, AdminSettingApiResource, \
    AdminSettingSiteResource, AdminInfoSettingOtherResource, \
    AdminEditSettingOtherResource, SystemStorageResource
from app.resources.admin.translate import AdminTranslateListResource, \
    AdminTranslateBatchDeleteResource, AdminTranslateRestartResource, AdminTranslateDeteleResource, \
    AdminTranslateStatisticsResource, AdminTranslateDownloadResource, \
    AdminTranslateDownloadBatchResource
from app.resources.admin.users import AdminUserListResource, AdminCreateUserResource, \
    AdminUserDetailResource, AdminUpdateUserResource, AdminDeleteUserResource, AdminResetPasswordResource
from app.resources.admin.tenant import AdminTenantListResource, AdminTenantDetailResource, \
    AdminCreateTenantResource, AdminUpdateTenantResource, AdminDeleteTenantResource, \
    AdminAssignCustomerToTenantResource, AdminAssignUserToTenantResource, AdminTenantStorageQuotaResource
from app.resources.admin.dashboard import DashboardStatisticsResource, DashboardTrendResource, \
    DashboardStatusDistributionResource, DashboardRecentTasksResource, DashboardSystemStatusResource
from app.resources.api.AccountResource import ChangePasswordResource, EmailChangePasswordResource, \
    StorageInfoResource, UserInfoResource, SendChangeCodeResource
from flask_restful import Resource
from app.translate.db import health_check
from app.resources.api.AuthResource import SendRegisterCodeResource, UserRegisterResource, \
    UserLoginResource, SendResetCodeResource, ResetPasswordResource, UserLogoutResource
from app.resources.api.comparison import MyComparisonListResource, SharedComparisonListResource, \
    EditComparisonResource, ShareComparisonResource, CopyComparisonResource, \
    FavoriteComparisonResource, CreateComparisonResource, DeleteComparisonResource, \
    DownloadTemplateResource, ImportComparisonResource, ExportComparisonResource, \
    ExportAllComparisonsResource, ComparisonTermsResource, ComparisonTermEditResource, \
    ComparisonTermDeleteResource
from app.resources.api.customer import GuestIdResource, CustomerDetailResource
from app.resources.api.doc2x import Doc2XTranslateStartResource, Doc2XTranslateStatusResource
from app.resources.api.files import FileUploadResource, FileDeleteResource
from app.resources.api.prompt import MyPromptListResource, SharedPromptListResource, \
    EditPromptResource, SharePromptResource, CopyPromptResource, FavoritePromptResource, \
    CreatePromptResource, DeletePromptResource
from app.resources.api.setting import SystemVersionResource, SystemSettingsResource
from app.resources.api.translate import TranslateListResource, TranslateSettingResource, \
    TranslateProcessResource, TranslateDeleteResource, TranslateDownloadResource, \
    OpenAICheckResource, PDFCheckResource, TranslateTestResource, TranslateDeleteAllResource, \
    TranslateFinishCountResource, TranslateRandDeleteAllResource, TranslateRandDeleteResource, \
    TranslateRandDownloadResource, Doc2xCheckResource, TranslateStartResource, \
    TranslateDownloadAllResource, TranslateProgressResource, QueueStatusResource
from app.resources.api.video import VideoUploadResource, VideoTranslateResource, VideoStatusResource, \
    VideoListResource, VideoDeleteResource, VideoDownloadResource, VideoLanguagesResource, VideoVoicesResource, VideoWebhookResource, VideoTokenInfoResource
from app.resources.api.tools import ImageUploadResource, ImageTranslateResource, ImageTranslateBatchResource, ImageTranslateStatusResource, ImageListResource, ImageDeleteResource, ImageBatchDeleteResource, ImageTranslateRetryResource, ImageTranslateBatchDownloadResource, PDFToImageResource


def register_routes(api):
    # 🏥 健康检查端点 - 使用Flask-RESTful方式注册
    class HealthCheckResource(Resource):
        def get(self):
            try:
                db_health = health_check()
                return {
                    'status': 'ok',
                    'database': db_health['status'],
                    'message': 'DocTranslator服务运行正常'
                }, 200
            except Exception as e:
                return {
                    'status': 'error',
                    'database': 'unhealthy',
                    'message': f'服务异常: {str(e)}'
                }, 500
    
    api.add_resource(HealthCheckResource, '/health')
    
    # 基础测试路由
    api.add_resource(SendRegisterCodeResource, '/api/register/send')
    api.add_resource(UserRegisterResource, '/api/register')
    api.add_resource(UserLoginResource, '/api/login')
    api.add_resource(UserLogoutResource, '/api/logout')
    api.add_resource(SendResetCodeResource, '/api/find/send')
    api.add_resource(ResetPasswordResource, '/api/find')

    api.add_resource(ChangePasswordResource, '/api/change')
    api.add_resource(SendChangeCodeResource, '/api/change/send')
    api.add_resource(EmailChangePasswordResource, '/api/change/email')
    api.add_resource(StorageInfoResource, '/api/storage')
    api.add_resource(UserInfoResource, '/api/user-info')

    api.add_resource(FileUploadResource, '/api/upload')
    api.add_resource(FileDeleteResource, '/api/delFile')

    api.add_resource(TranslateListResource, '/api/translates')
    api.add_resource(TranslateSettingResource, '/api/translate/setting')
    api.add_resource(TranslateProcessResource, '/api/process')
    api.add_resource(TranslateDeleteResource, '/api/translate/<int:id>')
    api.add_resource(TranslateDownloadResource, '/api/translate/download/<int:id>')
    api.add_resource(TranslateDownloadAllResource, '/api/translate/download/all')
    api.add_resource(OpenAICheckResource, '/api/check/openai')
    api.add_resource(PDFCheckResource, '/api/check/pdf')
    api.add_resource(TranslateTestResource, '/api/translate/test')
    api.add_resource(TranslateDeleteAllResource, '/api/translate/all')
    api.add_resource(TranslateFinishCountResource, '/api/translate/finish/count')
    api.add_resource(TranslateRandDeleteAllResource, '/api/translate/rand/all')
    api.add_resource(TranslateRandDeleteResource, '/api/translate/rand/<int:id>')
    api.add_resource(TranslateRandDownloadResource, '/api/translate/download/rand')
    api.add_resource(Doc2xCheckResource, '/api/check/doc2x')
    api.add_resource(TranslateStartResource, '/api/translate')  # 启动翻译
    api.add_resource(TranslateProgressResource, '/api/translate/progress')  # 查询翻译进度
    api.add_resource(QueueStatusResource, '/api/translate/queue-status')  # 查询队列状态
    # doc2x接口
    api.add_resource(Doc2XTranslateStartResource, '/api/doc2x/start')
    api.add_resource(Doc2XTranslateStatusResource, '/api/doc2x/status')

    api.add_resource(GuestIdResource, '/api/guest/id')
    api.add_resource(CustomerDetailResource, '/api/customer/<int:customer_id>')

    api.add_resource(MyComparisonListResource, '/api/comparison/my')
    api.add_resource(SharedComparisonListResource, '/api/comparison/share')
    api.add_resource(EditComparisonResource, '/api/comparison/<int:id>')
    api.add_resource(ShareComparisonResource, '/api/comparison/share/<int:id>')
    api.add_resource(CopyComparisonResource, '/api/comparison/copy/<int:id>')
    api.add_resource(FavoriteComparisonResource, '/api/comparison/fav/<int:id>')
    api.add_resource(CreateComparisonResource, '/api/comparison')
    api.add_resource(DeleteComparisonResource, '/api/comparison/<int:id>')
    api.add_resource(DownloadTemplateResource, '/api/comparison/template')
    api.add_resource(ImportComparisonResource, '/api/comparison/import')
    api.add_resource(ExportComparisonResource, '/api/comparison/export/<int:id>')
    api.add_resource(ExportAllComparisonsResource, '/api/comparison/export/all')
    api.add_resource(ComparisonTermsResource, '/api/comparison/<int:comparison_id>/terms')
    api.add_resource(ComparisonTermEditResource, '/api/comparison/term/<int:term_id>')
    api.add_resource(ComparisonTermDeleteResource, '/api/comparison/term/<int:term_id>')

    api.add_resource(SystemVersionResource, '/api/common/version')
    api.add_resource(SystemSettingsResource, '/api/common/all_settings')

    api.add_resource(MyPromptListResource, '/api/prompt/my')
    api.add_resource(SharedPromptListResource, '/api/prompt/share')
    api.add_resource(EditPromptResource, '/api/prompt/<int:id>')
    api.add_resource(SharePromptResource, '/api/prompt/share/<int:id>')
    api.add_resource(CopyPromptResource, '/api/prompt/copy/<int:id>')
    api.add_resource(FavoritePromptResource, '/api/prompt/fav/<int:id>')
    api.add_resource(CreatePromptResource, '/api/prompt')
    api.add_resource(DeletePromptResource, '/api/prompt/<int:id>')

    # 视频翻译接口
    api.add_resource(VideoUploadResource, '/api/video/upload')
    api.add_resource(VideoTranslateResource, '/api/video/translate')
    api.add_resource(VideoStatusResource, '/api/video/status/<int:video_id>')
    api.add_resource(VideoListResource, '/api/video/list')
    api.add_resource(VideoDeleteResource, '/api/video/<int:video_id>')
    api.add_resource(VideoDownloadResource, '/api/video/<int:video_id>/download')
    api.add_resource(VideoLanguagesResource, '/api/video/languages')
    api.add_resource(VideoVoicesResource, '/api/video/voices')
    api.add_resource(VideoWebhookResource, '/api/video/webhook/<int:video_id>')
    api.add_resource(VideoTokenInfoResource, '/api/video/token-info')

    # 工具接口
    api.add_resource(ImageUploadResource, '/api/tools/image-upload')
    api.add_resource(ImageTranslateResource, '/api/tools/image-translate')
    api.add_resource(ImageTranslateBatchResource, '/api/tools/image-translate/batch')
    api.add_resource(ImageTranslateStatusResource, '/api/tools/image-translate/status/<int:image_id>')
    api.add_resource(ImageListResource, '/api/tools/images')
    api.add_resource(ImageDeleteResource, '/api/tools/image/<int:image_id>')
    api.add_resource(ImageBatchDeleteResource, '/api/tools/images/batch-delete')
    api.add_resource(ImageTranslateRetryResource, '/api/tools/image-translate/retry/<int:image_id>')
    api.add_resource(ImageTranslateBatchDownloadResource, '/api/tools/images/batch-download')
    api.add_resource(PDFToImageResource, '/api/tools/pdf-to-image')


# -------admin-----------
    api.add_resource(AdminLoginResource, '/api/admin/login')
    api.add_resource(AdminChangePasswordResource, '/api/admin/changepwd')

    api.add_resource(AdminCustomerListResource, '/api/admin/customers')
    api.add_resource(AdminCreateCustomerResource, '/api/admin/customer')
    api.add_resource(AdminCustomerDetailResource, '/api/admin/customer/<int:id>')
    api.add_resource(AdminUpdateCustomerResource, '/api/admin/customer/<int:id>')
    api.add_resource(AdminDeleteCustomerResource, '/api/admin/customer/<int:id>')
    api.add_resource(CustomerStatusResource, '/api/admin/customer/status/<int:id>')

    api.add_resource(AdminUserListResource, '/api/admin/users')
    api.add_resource(AdminCreateUserResource, '/api/admin/user')
    api.add_resource(AdminUserDetailResource, '/api/admin/user/<int:id>')
    api.add_resource(AdminUpdateUserResource, '/api/admin/user/<int:id>')
    api.add_resource(AdminDeleteUserResource, '/api/admin/user/<int:id>')
    api.add_resource(AdminResetPasswordResource, '/api/admin/user/<int:id>/reset-password')

    # 租户管理接口（超级管理员专用）
    api.add_resource(AdminTenantListResource, '/api/admin/tenants')
    api.add_resource(AdminTenantDetailResource, '/api/admin/tenant/<int:id>')
    api.add_resource(AdminCreateTenantResource, '/api/admin/tenant')
    api.add_resource(AdminUpdateTenantResource, '/api/admin/tenant/<int:id>')
    api.add_resource(AdminDeleteTenantResource, '/api/admin/tenant/<int:id>')
    api.add_resource(AdminAssignCustomerToTenantResource, '/api/admin/tenant/assign-customer')
    api.add_resource(AdminAssignUserToTenantResource, '/api/admin/tenant/assign-user')
    api.add_resource(AdminTenantStorageQuotaResource, '/api/admin/tenant/<int:id>/storage-quota')

    api.add_resource(AdminTranslateListResource, '/api/admin/translates')
    api.add_resource(AdminTranslateDeteleResource, '/api/admin/translate/<int:id>')
    api.add_resource(AdminTranslateBatchDeleteResource, '/api/admin/translates/delete/batch')
    api.add_resource(AdminTranslateRestartResource, '/api/admin/translate/<int:id>/restart')
    api.add_resource(AdminTranslateStatisticsResource, '/api/admin/translate/statistics')
    api.add_resource(AdminTranslateDownloadResource, '/api/admin/translate/download/<int:id>')
    api.add_resource(AdminTranslateDownloadBatchResource,'/api/admin/translates/download/batch')

    api.add_resource(AdminImageResource, '/api/admin/image')

    api.add_resource(AdminSettingNoticeResource, '/api/admin/setting/notice')
    api.add_resource(AdminSettingApiResource, '/api/admin/setting/api')
    api.add_resource(AdminInfoSettingOtherResource, '/api/admin/setting/other')
    api.add_resource(AdminEditSettingOtherResource, '/api/admin/setting/other')
    api.add_resource(AdminSettingSiteResource, '/api/admin/setting/site')

    # 系统文件存储管理
    api.add_resource(SystemStorageResource, '/api/admin/system/storages')
    
    # 看板API
    api.add_resource(DashboardStatisticsResource, '/api/admin/dashboard/statistics')
    api.add_resource(DashboardTrendResource, '/api/admin/dashboard/trend')
    api.add_resource(DashboardStatusDistributionResource, '/api/admin/dashboard/status-distribution')
    api.add_resource(DashboardRecentTasksResource, '/api/admin/dashboard/recent-tasks')
    api.add_resource(DashboardSystemStatusResource, '/api/admin/dashboard/system-status')
    
    # print("✅ 路由配置完成")  # 添加调试输出
    # print("✅ 文件存储管理路由已注册: /api/admin/system/storages")  # 添加调试输出
    # print("✅ 看板路由已注册")  # 添加调试输出
    # api.add_resource(TodoListResource, '/todos')
    # api.add_resource(TodoResource, '/todos/<int:todo_id>')
