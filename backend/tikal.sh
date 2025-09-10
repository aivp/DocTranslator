#!/bin/bash
# 设置 Java XML 解析器限制，解决 "Maximum attribute size limit exceeded" 问题
JAVA_OPTS="-Djdk.xml.entityExpansionLimit=100000"
JAVA_OPTS="$JAVA_OPTS -Djdk.xml.elementAttributeLimit=50000"
JAVA_OPTS="$JAVA_OPTS -Djdk.xml.totalEntitySizeLimit=200000000"
JAVA_OPTS="$JAVA_OPTS -Djdk.xml.maxParameterEntitySizeLimit=50000000"
JAVA_OPTS="$JAVA_OPTS -Djdk.xml.entityReplacementLimit=100000000"
JAVA_OPTS="$JAVA_OPTS -Djdk.xml.maxElementDepth=1000"
JAVA_OPTS="$JAVA_OPTS -Djdk.xml.maxXMLNameLimit=10000"
JAVA_OPTS="$JAVA_OPTS -Djdk.xml.maxOccurLimit=50000"
JAVA_OPTS="$JAVA_OPTS -Djdk.xml.maxGeneralEntitySizeLimit=50000000"
# Xerces 特定限制（最关键）
JAVA_OPTS="$JAVA_OPTS -Dxerces.maxAttributeSize=50000000"
JAVA_OPTS="$JAVA_OPTS -Dxerces.maxTextLength=100000000"
JAVA_OPTS="$JAVA_OPTS -Dxerces.maxAttributeCount=100000"
# 内存设置
JAVA_OPTS="$JAVA_OPTS -Xmx2g"
JAVA_OPTS="$JAVA_OPTS -XX:MaxMetaspaceSize=512m"
# 执行 Tikal
java $JAVA_OPTS -cp "`dirname $0`/lib/*" net.sf.okapi.applications.tikal.Main "$@"