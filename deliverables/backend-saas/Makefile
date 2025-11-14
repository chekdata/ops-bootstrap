openapi:
	@echo "Generating OpenAPI spec..."
	mkdir -p build/swagger
	mvn -B -DskipTests=true -DskipITs=true -Popenapi springdoc-openapi:generate
	mv target/swagger.json build/swagger/swagger.json




