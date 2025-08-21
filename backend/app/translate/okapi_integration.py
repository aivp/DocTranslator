"""
Okapi Framework 集成模块

使用 Okapi Framework 进行 Word 文档翻译，解决 run 切割过细的问题。
通过 XLIFF 格式保持完整格式和上下文。

作者：Claude
版本：1.0.0
"""

import os
import subprocess
import tempfile
import shutil
import logging
import time
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
import zipfile

# 配置日志
logger = logging.getLogger(__name__)

class OkapiIntegrationError(Exception):
    """Okapi 集成错误"""
    pass

class DockerOkapiIntegration:
    """Docker 环境中的 Okapi 集成类"""
    
    def __init__(self, okapi_home: str = "/opt/okapi"):
        """
        初始化 Okapi 集成
        
        Args:
            okapi_home: Okapi 安装目录
        """
        self.okapi_home = okapi_home
        self.tikal_jar = os.path.join(okapi_home, "lib", "tikal.jar")
        
        # 验证 Okapi 安装
        if not os.path.exists(self.tikal_jar):
            raise OkapiIntegrationError(f"Tikal JAR 文件不存在: {self.tikal_jar}")
        
        # 验证 Java 环境
        self._verify_java_environment()
        
        logger.info(f"Okapi 集成初始化完成: {okapi_home}")
    
    def _verify_java_environment(self) -> bool:
        """验证 Java 环境是否可用"""
        try:
            result = subprocess.run(
                ["java", "-version"],
                capture_output=True,
                timeout=10
            )
            if result.returncode != 0:
                raise OkapiIntegrationError("Java 不可用")
            
            logger.info("Java 环境验证通过")
            return True
            
        except Exception as e:
            raise OkapiIntegrationError(f"Java 环境验证失败: {e}")
    
    @contextmanager
    def temp_workspace(self):
        """创建临时工作空间"""
        temp_dir = tempfile.mkdtemp(prefix="okapi_work_")
        try:
            logger.debug(f"创建临时工作空间: {temp_dir}")
            yield temp_dir
        finally:
            # 自动清理临时文件
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.debug(f"清理工作空间: {temp_dir}")
    
    def extract_to_xliff(self, input_file: str, output_xliff: str, 
                        source_lang: str = "zh", target_lang: str = "en",
                        java_opts: Optional[str] = None) -> bool:
        """
        使用 Tikal 提取 Word 文档到 XLIFF
        
        Args:
            input_file: 输入的 Word 文档路径
            output_xliff: 输出的 XLIFF 文件路径
            source_lang: 源语言代码
            target_lang: 目标语言代码
            java_opts: Java 选项
            
        Returns:
            bool: 是否成功
        """
        try:
            # 准备 Java 命令
            java_cmd = ["java"]
            
            # 添加 Java 选项（内存设置等）
            if java_opts:
                java_cmd.extend(java_opts.split())
            elif os.getenv("JAVA_OPTS"):
                java_cmd.extend(os.getenv("JAVA_OPTS").split())
            else:
                java_cmd.extend(["-Xmx1g", "-Xms256m"])
            
            # 添加 Tikal 命令参数
            java_cmd.extend([
                "-jar", self.tikal_jar,
                "-x", input_file,           # 提取模式
                "-sl", source_lang,         # 源语言
                "-tl", target_lang,         # 目标语言
                "-o", output_xliff          # 输出文件
            ])
            
            logger.info(f"执行提取命令: {' '.join(java_cmd)}")
            
            # 记录执行时间
            start_time = time.time()
            
            # 执行 Java 进程
            result = subprocess.run(
                java_cmd,
                capture_output=True,
                text=True,
                timeout=120,  # 2分钟超时
                cwd="/app"    # Docker 容器内的工作目录
            )
            
            duration = time.time() - start_time
            logger.info(f"Tikal 提取完成，用时: {duration:.2f}秒")
            
            # 详细的结果处理
            if result.returncode == 0:
                logger.info(f"✅ Tikal 提取成功: {output_xliff}")
                if result.stdout:
                    logger.debug(f"STDOUT: {result.stdout}")
                return True
            else:
                logger.error(f"❌ Tikal 提取失败 (返回码: {result.returncode})")
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Tikal 执行超时")
            return False
        except FileNotFoundError:
            logger.error("❌ Java 或 Tikal 未找到")
            return False
        except Exception as e:
            logger.error(f"❌ 执行过程中出错: {e}")
            return False
    
    def merge_from_xliff(self, original_file: str, xliff_file: str, 
                        output_file: str, java_opts: Optional[str] = None) -> bool:
        """
        将翻译后的 XLIFF 合并回 Word 文档
        
        Args:
            original_file: 原始 Word 文档路径
            xliff_file: 翻译后的 XLIFF 文件路径
            output_file: 输出的 Word 文档路径
            java_opts: Java 选项
            
        Returns:
            bool: 是否成功
        """
        try:
            # 构建合并命令
            java_cmd = ["java"]
            
            # Java 选项
            if java_opts:
                java_cmd.extend(java_opts.split())
            else:
                java_cmd.extend(["-Xmx1g", "-Xms256m"])
            
            # Tikal 合并命令
            java_cmd.extend([
                "-jar", self.tikal_jar,
                "-m", xliff_file,           # 合并模式
                "-from", original_file,     # 原始文档
                "-o", output_file           # 输出文件
            ])
            
            logger.info(f"执行合并命令: {' '.join(java_cmd)}")
            
            # 记录执行时间
            start_time = time.time()
            
            # 执行 Java 进程
            result = subprocess.run(
                java_cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd="/app"
            )
            
            duration = time.time() - start_time
            logger.info(f"Tikal 合并完成，用时: {duration:.2f}秒")
            
            if result.returncode == 0:
                logger.info(f"✅ XLIFF 合并成功: {output_file}")
                if result.stdout:
                    logger.debug(f"STDOUT: {result.stdout}")
                return True
            else:
                logger.error(f"❌ XLIFF 合并失败: {result.stderr}")
                logger.error(f"STDOUT: {result.stdout}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 合并过程出错: {e}")
            return False
    
    def parse_xliff_content(self, xliff_file: str) -> List[Dict[str, Any]]:
        """
        解析 XLIFF 文件内容，提取需要翻译的文本
        
        Args:
            xliff_file: XLIFF 文件路径
            
        Returns:
            List[Dict]: 翻译单元列表
        """
        try:
            tree = ET.parse(xliff_file)
            root = tree.getroot()
            
            # 定义命名空间
            namespaces = {
                'xliff': 'urn:oasis:names:tc:xliff:document:2.0'
            }
            
            translation_units = []
            
            # 查找所有翻译单元
            for unit in root.findall('.//xliff:unit', namespaces):
                unit_id = unit.get('id', '')
                
                # 查找源文本和目标文本
                source_elem = unit.find('.//xliff:source', namespaces)
                target_elem = unit.find('.//xliff:target', namespaces)
                
                if source_elem is not None:
                    source_text = ''.join(source_elem.itertext()).strip()
                    
                    # 只处理有意义的文本
                    if source_text and len(source_text) > 0:
                        translation_units.append({
                            'id': unit_id,
                            'source': source_text,
                            'target': ''.join(target_elem.itertext()).strip() if target_elem is not None else '',
                            'unit_element': unit
                        })
            
            logger.info(f"解析到 {len(translation_units)} 个翻译单元")
            return translation_units
            
        except Exception as e:
            logger.error(f"解析 XLIFF 文件失败: {e}")
            return []
    
    def update_xliff_translations(self, xliff_file: str, translations: Dict[str, str]) -> bool:
        """
        更新 XLIFF 文件中的翻译内容
        
        Args:
            xliff_file: XLIFF 文件路径
            translations: 翻译结果字典 {unit_id: translated_text}
            
        Returns:
            bool: 是否成功
        """
        try:
            tree = ET.parse(xliff_file)
            root = tree.getroot()
            
            # 定义命名空间
            namespaces = {
                'xliff': 'urn:oasis:names:tc:xliff:document:2.0'
            }
            
            updated_count = 0
            
            # 更新每个翻译单元
            for unit in root.findall('.//xliff:unit', namespaces):
                unit_id = unit.get('id', '')
                
                if unit_id in translations:
                    # 查找或创建目标元素
                    target_elem = unit.find('.//xliff:target', namespaces)
                    if target_elem is None:
                        # 如果没有目标元素，创建一个
                        source_elem = unit.find('.//xliff:source', namespaces)
                        if source_elem is not None:
                            target_elem = ET.SubElement(unit, f'{{{namespaces["xliff"]}}}target')
                    
                    if target_elem is not None:
                        # 更新目标文本
                        target_elem.text = translations[unit_id]
                        updated_count += 1
            
            # 保存更新后的文件
            tree.write(xliff_file, encoding='utf-8', xml_declaration=True)
            
            logger.info(f"更新了 {updated_count} 个翻译单元")
            return True
            
        except Exception as e:
            logger.error(f"更新 XLIFF 翻译失败: {e}")
            return False


class OkapiWordTranslator:
    """使用 Okapi Framework 的 Word 文档翻译器"""
    
    def __init__(self, okapi_home: str = "/opt/okapi"):
        """
        初始化翻译器
        
        Args:
            okapi_home: Okapi 安装目录
        """
        self.okapi_integration = DockerOkapiIntegration(okapi_home)
        self.translation_service = None  # 翻译服务将在后续设置
        
        logger.info("Okapi Word 翻译器初始化完成")
    
    def set_translation_service(self, translation_service):
        """设置翻译服务"""
        self.translation_service = translation_service
        logger.info("翻译服务已设置")
    
    def translate_document(self, input_file: str, output_file: str,
                          source_lang: str = "zh", target_lang: str = "en") -> bool:
        """
        翻译 Word 文档
        
        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径
            source_lang: 源语言
            target_lang: 目标语言
            
        Returns:
            bool: 是否成功
        """
        if not self.translation_service:
            raise OkapiIntegrationError("翻译服务未设置")
        
        try:
            with self.okapi_integration.temp_workspace() as workspace:
                # 文件路径
                xliff_file = os.path.join(workspace, "extracted.xliff")
                translated_xliff = os.path.join(workspace, "translated.xliff")
                
                # 步骤1：Word 文档 → XLIFF
                logger.info("🔄 步骤1: 提取 Word 文档到 XLIFF...")
                success = self.okapi_integration.extract_to_xliff(
                    input_file, xliff_file, source_lang, target_lang
                )
                if not success:
                    return False
                
                # 步骤2：翻译 XLIFF 内容
                logger.info("🔄 步骤2: 翻译 XLIFF 内容...")
                success = self._translate_xliff_content(
                    xliff_file, translated_xliff, source_lang, target_lang
                )
                if not success:
                    return False
                
                # 步骤3：XLIFF → Word 文档
                logger.info("🔄 步骤3: 合并翻译后的 XLIFF 到 Word...")
                success = self.okapi_integration.merge_from_xliff(
                    input_file, translated_xliff, output_file
                )
                
                return success
                
        except Exception as e:
            logger.error(f"翻译过程出错: {e}")
            return False
    
    def _translate_xliff_content(self, xliff_file: str, translated_xliff: str,
                                source_lang: str, target_lang: str) -> bool:
        """
        翻译 XLIFF 文件中的内容
        
        Args:
            xliff_file: 原始 XLIFF 文件
            translated_xliff: 翻译后的 XLIFF 文件
            source_lang: 源语言
            target_lang: 目标语言
            
        Returns:
            bool: 是否成功
        """
        try:
            # 解析 XLIFF 内容
            translation_units = self.okapi_integration.parse_xliff_content(xliff_file)
            
            if not translation_units:
                logger.warning("没有找到需要翻译的内容")
                # 复制原文件
                shutil.copy2(xliff_file, translated_xliff)
                return True
            
            # 批量翻译
            translations = {}
            batch_texts = []
            batch_ids = []
            
            for unit in translation_units:
                batch_texts.append(unit['source'])
                batch_ids.append(unit['id'])
            
            logger.info(f"开始批量翻译 {len(batch_texts)} 个文本单元...")
            
            # 调用翻译服务
            translated_texts = self.translation_service.batch_translate(
                batch_texts, source_lang, target_lang
            )
            
            if len(translated_texts) != len(batch_texts):
                logger.error("翻译结果数量不匹配")
                return False
            
            # 构建翻译结果字典
            for i, unit_id in enumerate(batch_ids):
                translations[unit_id] = translated_texts[i]
            
            # 复制原文件并更新翻译
            shutil.copy2(xliff_file, translated_xliff)
            success = self.okapi_integration.update_xliff_translations(
                translated_xliff, translations
            )
            
            if success:
                logger.info(f"✅ XLIFF 内容翻译完成，共翻译 {len(translations)} 个单元")
            
            return success
            
        except Exception as e:
            logger.error(f"翻译 XLIFF 内容失败: {e}")
            return False


# 便捷函数
def create_okapi_translator(okapi_home: str = "/opt/okapi") -> OkapiWordTranslator:
    """创建 Okapi 翻译器实例"""
    return OkapiWordTranslator(okapi_home)


def verify_okapi_installation(okapi_home: str = "/opt/okapi") -> bool:
    """验证 Okapi 安装是否正确"""
    try:
        integration = DockerOkapiIntegration(okapi_home)
        logger.info("✅ Okapi 安装验证通过")
        return True
    except Exception as e:
        logger.error(f"❌ Okapi 安装验证失败: {e}")
        return False 