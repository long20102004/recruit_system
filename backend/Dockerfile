FROM maven:3.9.9-eclipse-temurin-17 AS build
WORKDIR /build
COPY pom.xml ./
COPY common/pom.xml common/pom.xml
COPY identity-service/pom.xml identity-service/pom.xml
COPY recruitment-service/pom.xml recruitment-service/pom.xml
COPY interview-service/pom.xml interview-service/pom.xml
COPY common/src common/src
COPY identity-service/src identity-service/src
COPY recruitment-service/src recruitment-service/src
COPY interview-service/src interview-service/src
ARG SERVICE
RUN mvn -B -pl ${SERVICE} -am package -DskipTests

FROM eclipse-temurin:17-jre
ARG SERVICE
WORKDIR /app
RUN useradd --system --uid 10001 hirelens && mkdir /app/uploads && chown hirelens /app/uploads
COPY --from=build /build/${SERVICE}/target/${SERVICE}-0.0.1-SNAPSHOT.jar /app/app.jar
USER hirelens
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
