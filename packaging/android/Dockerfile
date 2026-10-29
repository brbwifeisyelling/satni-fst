# Android-sovelluksen (android/) käännösympäristö: JDK 17, Android SDK ja Gradle. Käytetään
# build_apk.sh:sta, jottei Javaa tai Android SDK:ta tarvitse asentaa omalle koneelle.
FROM eclipse-temurin:17-jdk-jammy

RUN apt-get update && apt-get install -y --no-install-recommends unzip curl \
    && rm -rf /var/lib/apt/lists/*

ENV ANDROID_HOME=/opt/android-sdk
ARG CMDLINE_TOOLS=commandlinetools-linux-11076708_latest.zip
RUN mkdir -p $ANDROID_HOME/cmdline-tools \
    && curl -sSL -o /tmp/tools.zip https://dl.google.com/android/repository/$CMDLINE_TOOLS \
    && unzip -q /tmp/tools.zip -d $ANDROID_HOME/cmdline-tools \
    && mv $ANDROID_HOME/cmdline-tools/cmdline-tools $ANDROID_HOME/cmdline-tools/latest \
    && rm /tmp/tools.zip
RUN yes | $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager --licenses >/dev/null \
    && $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager "platforms;android-35" "build-tools;35.0.0" "platform-tools" >/dev/null

ARG GRADLE=8.10.2
RUN curl -sSL -o /tmp/gradle.zip https://services.gradle.org/distributions/gradle-$GRADLE-bin.zip \
    && unzip -q /tmp/gradle.zip -d /opt && ln -s /opt/gradle-$GRADLE/bin/gradle /usr/local/bin/gradle \
    && rm /tmp/gradle.zip
# Rakennus ajetaan käyttäjän omana uid:nä: SDK:n pitää olla luettavissa
RUN chmod -R a+rX $ANDROID_HOME
