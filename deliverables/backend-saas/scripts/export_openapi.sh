#!/usr/bin/env bash
set -euo pipefail

# Build the project (skip tests for speed in CI)
mvn -B -DskipTests=true -DskipITs=true clean package

# Find the built jar
JAR=$(ls -1 target/*.jar | head -n1)
if [ -z "${JAR:-}" ]; then
  echo "No jar found under target/" >&2
  exit 1
fi

mkdir -p build/swagger

# Start the app in a minimized 'openapi' profile on port 4010 and export OpenAPI
nohup bash -c "JAVA_TOOL_OPTIONS='-XX:+UseContainerSupport -XX:MaxRAMFraction=2' \
  SPRING_PROFILES_ACTIVE=openapi \
  SPRING_CLOUD_NACOS_CONFIG_ENABLED=false \
  SPRING_CLOUD_NACOS_DISCOVERY_ENABLED=false \
  SPRING_MAIN_ALLOW_BEAN_DEFINITION_OVERRIDING=true \
  java -Dspring.autoconfigure.exclude=org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration,org.springframework.boot.autoconfigure.jdbc.DataSourceTransactionManagerAutoConfiguration,org.mybatis.spring.boot.autoconfigure.MybatisAutoConfiguration,com.alibaba.cloud.nacos.NacosDiscoveryAutoConfiguration,com.alibaba.cloud.nacos.registry.NacosServiceRegistryAutoConfiguration \
  -Dserver.port=4010 -jar \"$JAR\" --spring.profiles.active=openapi > build/app.log 2>&1 &" >/dev/null 2>&1

# Probe /v3/api-docs up to ~6 minutes
for i in $(seq 1 180); do
  if curl -fsS http://127.0.0.1:4010/v3/api-docs -o build/swagger/swagger.json; then
    echo "OpenAPI exported to build/swagger/swagger.json"
    exit 0
  fi
  sleep 2
done

echo "OpenAPI export failed after waiting. Tail of build/app.log:" >&2
tail -n 400 build/app.log || true
exit 1




