Name:		ivy
Version:	2.6.0
Release:	2
Summary:	Dependency manager for Apache Ant
Group:		Development/Java
License:	Apache-2.0
URL:		https://ant.apache.org/ivy/
Source0:	https://downloads.apache.org/ant/ivy/%{version}/apache-ivy-%{version}-src.tar.gz
Source1:	https://downloads.apache.org/ant/ivy/2.5.3/apache-ivy-2.5.3-src.tar.gz
BuildArch:	noarch
BuildRequires:	java-current-devel
BuildRequires:	javapackages-filesystem
BuildRequires:	python
BuildRequires:	sysjar
BuildRequires:	ant >= 1.10.18
BuildRequires:	httpcomponents-client >= 4.5.14
BuildRequires:	httpcomponents-core >= 4.4.16
BuildRequires:	apache-commons-codec >= 1.23.0
BuildRequires:	apache-commons-logging >= 1.4.0
BuildRequires:	apache-commons-vfs >= 2.10.0
BuildRequires:	apache-commons-io >= 2.22.0
BuildRequires:	apache-commons-collections4 >= 4.6.0
BuildRequires:	apache-commons-lang3 >= 3.21.0
Requires:	java-current
Requires:	ant >= 1.10.18
Requires:	httpcomponents-client >= 4.5.14
Requires:	httpcomponents-core >= 4.4.16
Requires:	apache-commons-codec >= 1.23.0
Requires:	apache-commons-logging >= 1.4.0
Requires:	apache-commons-vfs >= 2.10.0
Requires:	apache-commons-io >= 2.22.0
Requires:	apache-commons-collections4 >= 4.6.0
Requires:	apache-commons-lang3 >= 3.21.0

%description
Apache Ivy resolves and retrieves project dependencies. This package
builds Ivy %{version} from source. The 2.5.3 jar is installed beside
it. The command line tool and the Ant tasks use the %{version} jar.

The build leaves out features whose libraries are not packaged. The
glob matcher needs Apache ORO. SFTP needs JSch. OpenPGP signatures
need Bouncy Castle. pack200 needs a commons-compress build that still
ships Pack200CompressorInputStream, and cooker has 1.28, which does
not. Ivy logs those gaps and keeps running.

2.6.0 adds a nearest conflict manager that follows Maven's rule,
merges extension namespaces in deliver, and fixes CVE-2026-26032, a
path traversal in PackagerResolver.

%prep
%setup -q -n apache-ivy-%{version}
%setup -q -T -D -a 1 -n apache-ivy-%{version}
# Example trees ship prebuilt jars. The build does not use them.
find . \( -name '*.jar' -o -name '*.class' -o -name '*.so' -o -name '*.node' -o -name '*.wasm' \) -delete

%build
export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java}"
JAVAC="$JAVA_HOME/bin/javac"
SRC=src/java
mkdir -p build/core build/ant build/opt build/classes

python - << 'PY'
from pathlib import Path
src = Path("src/java")
skip_prefix = (
    "org/apache/ivy/plugins/repository/sftp/",
    "org/apache/ivy/plugins/repository/ssh/",
    "org/apache/ivy/plugins/signer/bouncycastle/",
)
skip_file = {
    "org/apache/ivy/plugins/matcher/GlobPatternMatcher.java",
    "org/apache/ivy/plugins/pack/Pack200Packing.java",
    "org/apache/ivy/plugins/pack/Pack200Util.java",
    "org/apache/ivy/plugins/resolver/AbstractSshBasedResolver.java",
    "org/apache/ivy/plugins/resolver/SFTPResolver.java",
    "org/apache/ivy/plugins/resolver/SshResolver.java",
}
opt_prefix = (
    "org/apache/ivy/plugins/repository/vfs/",
    "org/apache/ivy/plugins/repository/vsftp/",
)
opt_file = {
    "org/apache/ivy/plugins/resolver/VfsResolver.java",
    "org/apache/ivy/plugins/resolver/VsftpResolver.java",
    "org/apache/ivy/util/url/HttpClientHandler.java",
}
core, ant, opt = [], [], []
for path in sorted(src.rglob("*.java")):
    rel = path.relative_to(src).as_posix()
    if rel in skip_file or any(rel.startswith(prefix) for prefix in skip_prefix):
        continue
    if rel.startswith("org/apache/ivy/ant/") or rel.startswith("org/apache/ivy/plugins/resolver/packager/"):
        ant.append(str(path))
    elif rel in opt_file or any(rel.startswith(prefix) for prefix in opt_prefix):
        opt.append(str(path))
    else:
        core.append(str(path))
Path("build/core.list").write_text("\n".join(core) + "\n")
Path("build/ant.list").write_text("\n".join(ant) + "\n")
Path("build/opt.list").write_text("\n".join(opt) + "\n")
if not core or not ant or not opt:
    raise SystemExit("incomplete ivy source lists")
PY

"$JAVAC" --release 8 -proc:none -d build/core -sourcepath "$SRC" @build/core.list
"$JAVAC" --release 8 -proc:none -d build/ant \
	-classpath "build/core:%{_javadir}/ant.jar" \
	-sourcepath "$SRC" @build/ant.list
"$JAVAC" --release 8 -proc:none -d build/opt \
	-classpath "build/core:build/ant:%{_javadir}/ant.jar:%{_javadir}/commons-vfs2.jar:%{_javadir}/httpcomponents/httpclient.jar:%{_javadir}/httpcomponents/httpcore.jar:%{_javadir}/commons-codec.jar" \
	-sourcepath "$SRC" @build/opt.list

cp -a build/core/. build/classes/
cp -a build/ant/. build/classes/
cp -a build/opt/. build/classes/
find "$SRC" -type f ! -name '*.java' -print | while IFS= read -r file; do
	rel=${file#"$SRC"/}
	mkdir -p "build/classes/$(dirname "$rel")"
	cp -p "$file" "build/classes/$rel"
done
settings=build/classes/org/apache/ivy/core/settings
cp -p "$settings/ivysettings-local.xml" "$settings/ivyconf-local.xml"
cp -p "$settings/ivysettings-default-chain.xml" "$settings/ivyconf-default-chain.xml"
cp -p "$settings/ivysettings-main-chain.xml" "$settings/ivyconf-main-chain.xml"
cp -p "$settings/ivysettings-public.xml" "$settings/ivyconf-public.xml"
cp -p "$settings/ivysettings-shared.xml" "$settings/ivyconf-shared.xml"
cp -p "$settings/ivysettings.xml" "$settings/ivyconf.xml"
# Upstream stamps this at release time. 20260712061200 is the 2.6.0
# source archive timestamp, kept fixed so the jar does not change per build.
echo "version=%{version}" > build/classes/module.properties
echo "date=20260712061200" >> build/classes/module.properties

python - << 'PY'
from pathlib import Path
text = Path("META-INF/MANIFEST.MF").read_text()
if not text.endswith("\n"):
    text += "\n"
text += (
    "Implementation-Title: Apache Ivy\n"
    "Implementation-Version: %{version}\n"
    "Implementation-Vendor: Apache Software Foundation\n"
)
Path("build/MANIFEST.MF").write_text(text)
PY
"$JAVA_HOME/bin/jar" cfm build/ivy.jar build/MANIFEST.MF -C build/classes .
test -s build/ivy.jar

python - << 'PY'
from pathlib import Path
Path("build/ivy.pom").write_text("""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.apache.ivy</groupId>
  <artifactId>ivy</artifactId>
  <version>%{version}</version>
  <name>Apache Ivy</name>
  <description>Dependency manager used with Apache Ant. Optional features that are not packaged are omitted.</description>
  <url>https://ant.apache.org/ivy/</url>
  <licenses>
    <license>
      <name>Apache-2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0.txt</url>
      <distribution>repo</distribution>
    </license>
  </licenses>
  <dependencies>
    <dependency>
      <groupId>org.apache.ant</groupId>
      <artifactId>ant</artifactId>
      <version>1.10.18</version>
      <optional>true</optional>
    </dependency>
    <dependency>
      <groupId>org.apache.httpcomponents</groupId>
      <artifactId>httpclient</artifactId>
      <version>4.5.14</version>
      <optional>true</optional>
    </dependency>
    <dependency>
      <groupId>org.apache.commons</groupId>
      <artifactId>commons-vfs2</artifactId>
      <version>2.10.0</version>
      <optional>true</optional>
    </dependency>
  </dependencies>
</project>
""")
PY

# org.apache.ivy:ivy 2.5.3 stays beside %{version}. The command and
# the Ant lib symlink keep the %{version} jar.
(
cd apache-ivy-2.5.3
mkdir -p build/core build/ant build/opt build/classes
python - << 'PY'
from pathlib import Path
src = Path("src/java")
skip_prefix = (
    "org/apache/ivy/plugins/repository/sftp/",
    "org/apache/ivy/plugins/repository/ssh/",
    "org/apache/ivy/plugins/signer/bouncycastle/",
)
skip_file = {
    "org/apache/ivy/plugins/matcher/GlobPatternMatcher.java",
    "org/apache/ivy/plugins/pack/Pack200Packing.java",
    "org/apache/ivy/plugins/pack/Pack200Util.java",
    "org/apache/ivy/plugins/resolver/AbstractSshBasedResolver.java",
    "org/apache/ivy/plugins/resolver/SFTPResolver.java",
    "org/apache/ivy/plugins/resolver/SshResolver.java",
}
opt_prefix = (
    "org/apache/ivy/plugins/repository/vfs/",
    "org/apache/ivy/plugins/repository/vsftp/",
)
opt_file = {
    "org/apache/ivy/plugins/resolver/VfsResolver.java",
    "org/apache/ivy/plugins/resolver/VsftpResolver.java",
    "org/apache/ivy/util/url/HttpClientHandler.java",
}
core, ant, opt = [], [], []
for path in sorted(src.rglob("*.java")):
    rel = path.relative_to(src).as_posix()
    if rel in skip_file or any(rel.startswith(prefix) for prefix in skip_prefix):
        continue
    if rel.startswith("org/apache/ivy/ant/") or rel.startswith("org/apache/ivy/plugins/resolver/packager/"):
        ant.append(str(path))
    elif rel in opt_file or any(rel.startswith(prefix) for prefix in opt_prefix):
        opt.append(str(path))
    else:
        core.append(str(path))
Path("build/core.list").write_text("\n".join(core) + "\n")
Path("build/ant.list").write_text("\n".join(ant) + "\n")
Path("build/opt.list").write_text("\n".join(opt) + "\n")
if not core or not ant or not opt:
    raise SystemExit("incomplete ivy 2.5.3 source lists")
PY
"$JAVAC" --release 8 -proc:none -d build/core -sourcepath src/java @build/core.list
"$JAVAC" --release 8 -proc:none -d build/ant \
	-classpath "build/core:%{_javadir}/ant.jar" \
	-sourcepath src/java @build/ant.list
"$JAVAC" --release 8 -proc:none -d build/opt \
	-classpath "build/core:build/ant:%{_javadir}/ant.jar:%{_javadir}/commons-vfs2.jar:%{_javadir}/httpcomponents/httpclient.jar:%{_javadir}/httpcomponents/httpcore.jar:%{_javadir}/commons-codec.jar" \
	-sourcepath src/java @build/opt.list
cp -a build/core/. build/classes/
cp -a build/ant/. build/classes/
cp -a build/opt/. build/classes/
find src/java -type f ! -name '*.java' -print | while IFS= read -r file; do
	rel=${file#src/java/}
	mkdir -p "build/classes/$(dirname "$rel")"
	cp -p "$file" "build/classes/$rel"
done
settings=build/classes/org/apache/ivy/core/settings
cp -p "$settings/ivysettings-local.xml" "$settings/ivyconf-local.xml"
cp -p "$settings/ivysettings-default-chain.xml" "$settings/ivyconf-default-chain.xml"
cp -p "$settings/ivysettings-main-chain.xml" "$settings/ivyconf-main-chain.xml"
cp -p "$settings/ivysettings-public.xml" "$settings/ivyconf-public.xml"
cp -p "$settings/ivysettings-shared.xml" "$settings/ivyconf-shared.xml"
cp -p "$settings/ivysettings.xml" "$settings/ivyconf.xml"
# 20241223115459 is the newest 2.5.3 src/java timestamp.
echo "version=2.5.3" > build/classes/module.properties
echo "date=20241223115459" >> build/classes/module.properties
python - << 'PY'
from pathlib import Path
text = Path("META-INF/MANIFEST.MF").read_text()
if not text.endswith("\n"):
    text += "\n"
text += (
    "Implementation-Title: Apache Ivy\n"
    "Implementation-Version: 2.5.3\n"
    "Implementation-Vendor: Apache Software Foundation\n"
)
Path("build/MANIFEST.MF").write_text(text)
Path("build/ivy.pom").write_text("""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.apache.ivy</groupId>
  <artifactId>ivy</artifactId>
  <version>2.5.3</version>
  <name>Apache Ivy</name>
  <description>Dependency manager used with Apache Ant. Optional features that are not packaged are omitted.</description>
  <url>https://ant.apache.org/ivy/</url>
  <licenses>
    <license>
      <name>Apache-2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0.txt</url>
      <distribution>repo</distribution>
    </license>
  </licenses>
  <dependencies>
    <dependency>
      <groupId>org.apache.ant</groupId>
      <artifactId>ant</artifactId>
      <version>1.10.18</version>
      <optional>true</optional>
    </dependency>
    <dependency>
      <groupId>org.apache.httpcomponents</groupId>
      <artifactId>httpclient</artifactId>
      <version>4.5.14</version>
      <optional>true</optional>
    </dependency>
    <dependency>
      <groupId>org.apache.commons</groupId>
      <artifactId>commons-vfs2</artifactId>
      <version>2.10.0</version>
      <optional>true</optional>
    </dependency>
  </dependencies>
</project>
""")
PY
"$JAVA_HOME/bin/jar" cfm build/ivy.jar build/MANIFEST.MF -C build/classes .
test -s build/ivy.jar
)

%install
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_sysconfdir}/ant.d
mkdir -p %{buildroot}%{_datadir}/ant/lib
ln -s ../../java/ivy.jar %{buildroot}%{_datadir}/ant/lib/ivy.jar

cat > %{buildroot}%{_bindir}/ivy << 'EOF'
#!/bin/sh
if [ -z "${JAVA_HOME:-}" ]; then
	JAVA_HOME=/usr/lib/jvm/java
fi
CP=%{_javadir}/ivy.jar
for jar in \
	%{_javadir}/httpcomponents/httpclient.jar \
	%{_javadir}/httpcomponents/httpcore.jar \
	%{_javadir}/commons-codec.jar \
	%{_javadir}/commons-logging.jar \
	%{_javadir}/commons-vfs2.jar \
	%{_javadir}/commons-io.jar \
	%{_javadir}/commons-collections4.jar \
	%{_javadir}/commons-lang3.jar
do
	if [ -f "$jar" ]; then
		CP=$CP:$jar
	fi
done
exec "$JAVA_HOME/bin/java" -cp "$CP" org.apache.ivy.Main "$@"
EOF
chmod 755 %{buildroot}%{_bindir}/ivy

: > %{buildroot}%{_sysconfdir}/ant.d/ivy
for jar in \
	%{_javadir}/httpcomponents/httpclient.jar \
	%{_javadir}/httpcomponents/httpcore.jar \
	%{_javadir}/commons-codec.jar \
	%{_javadir}/commons-logging.jar \
	%{_javadir}/commons-vfs2.jar \
	%{_javadir}/commons-io.jar \
	%{_javadir}/commons-collections4.jar \
	%{_javadir}/commons-lang3.jar
do
	echo "$jar" >> %{buildroot}%{_sysconfdir}/ant.d/ivy
done

sysjar install --buildroot %{buildroot} \
	--artifact "apache-ivy-2.5.3/build/ivy.pom:apache-ivy-2.5.3/build/ivy.jar" \
	--file-name ivy-2.5.3 \
	--filelist .mfiles253
# %{version} owns ivy.sysjar. 2.5.3 keeps a second index.
/bin/mv %{buildroot}/usr/share/sysjar/index/org.apache.ivy/ivy.sysjar \
	%{buildroot}/usr/share/sysjar/index/org.apache.ivy/ivy-2.5.3.sysjar
sed -i 's|/usr/share/sysjar/index/org.apache.ivy/ivy\.sysjar|/usr/share/sysjar/index/org.apache.ivy/ivy-2.5.3.sysjar|' .mfiles253

sysjar install --buildroot %{buildroot} \
	--artifact "build/ivy.pom:build/ivy.jar" \
	--file-name ivy \
	--filelist .mfiles
while IFS= read -r line; do
	grep -qxF -- "$line" .mfiles || printf '%s\n' "$line" >> .mfiles
done < .mfiles253

%check
export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java}"
deps="%{_javadir}/httpcomponents/httpclient.jar:%{_javadir}/httpcomponents/httpcore.jar:%{_javadir}/commons-codec.jar:%{_javadir}/commons-logging.jar:%{_javadir}/commons-vfs2.jar:%{_javadir}/commons-io.jar:%{_javadir}/commons-collections4.jar:%{_javadir}/commons-lang3.jar"
"$JAVA_HOME/bin/java" -cp "build/ivy.jar:$deps" org.apache.ivy.Main -version > check-version.log
grep -F -q 'Apache Ivy %{version}' check-version.log

cat > IvyCheck.java << 'EOF'
public class IvyCheck {
    public static void main(String[] args) throws Exception {
        Object handler = org.apache.ivy.util.url.URLHandlerRegistry.getHttp();
        String name = handler.getClass().getName();
        if (!name.equals("org.apache.ivy.util.url.HttpClientHandler")) {
            throw new RuntimeException(name);
        }
        org.apache.ivy.plugins.repository.vfs.VfsRepository repo =
            new org.apache.ivy.plugins.repository.vfs.VfsRepository();
        java.lang.reflect.Method method = repo.getClass().getDeclaredMethod("createVFSManager");
        method.setAccessible(true);
        method.invoke(repo);
        System.out.println("handlers ok");
    }
}
EOF
"$JAVA_HOME/bin/javac" --release 8 -proc:none -cp build/ivy.jar IvyCheck.java
"$JAVA_HOME/bin/java" -cp "build/ivy.jar:$deps:." IvyCheck > check-handlers.log
grep -F -q 'handlers ok' check-handlers.log

mkdir -p check/repo/org.example/lib/1.0 check/home/lib check/src
echo 'public class Lib { public static int n() { return 7; } }' > check/src/Lib.java
"$JAVA_HOME/bin/javac" --release 8 -d check/src check/src/Lib.java
"$JAVA_HOME/bin/jar" cf check/repo/org.example/lib/1.0/lib.jar -C check/src Lib.class
cat > check/repo/org.example/lib/1.0/ivy.xml << 'EOF'
<ivy-module version="2.0">
  <info organisation="org.example" module="lib" revision="1.0" status="release"/>
  <publications>
    <artifact name="lib" type="jar" ext="jar"/>
  </publications>
</ivy-module>
EOF
cat > check/ivy.xml << 'EOF'
<ivy-module version="2.0">
  <info organisation="org.example" module="app" revision="1.0"/>
  <dependencies>
    <dependency org="org.example" name="lib" rev="1.0"/>
  </dependencies>
</ivy-module>
EOF
cat > check/ivysettings.xml << 'EOF'
<ivysettings>
  <settings defaultResolver="local"/>
  <caches defaultCacheDir="${ivy.settings.dir}/cache"/>
  <resolvers>
    <filesystem name="local">
      <ivy pattern="${ivy.settings.dir}/repo/[organisation]/[module]/[revision]/ivy.xml"/>
      <artifact pattern="${ivy.settings.dir}/repo/[organisation]/[module]/[revision]/[artifact].[ext]"/>
    </filesystem>
  </resolvers>
</ivysettings>
EOF
cat > check/build.xml << 'EOF'
<project xmlns:ivy="antlib:org.apache.ivy.ant" default="t">
  <target name="t">
    <ivy:settings file="ivysettings.xml"/>
    <ivy:resolve file="ivy.xml"/>
    <ivy:retrieve pattern="ant-out/[artifact].[ext]"/>
    <echo message="ant ivy ok"/>
  </target>
</project>
EOF
ln -s %{_javadir}/ant.jar check/home/lib/ant.jar
ln -s %{_javadir}/ant-launcher.jar check/home/lib/ant-launcher.jar
ln -s "$PWD/build/ivy.jar" check/home/lib/ivy.jar
# A private ANT_HOME makes the launcher read these jars. The system
# Ant script ignores ANT_HOME/lib when rpm_mode is on.
(
	cd check
	ANT_HOME="$PWD/home" "$JAVA_HOME/bin/java" -version >/dev/null
	ANT_HOME="$PWD/home" JAVA_HOME="$JAVA_HOME" /usr/bin/ant -noinput > ant.log
)
grep -F -q 'ant ivy ok' check/ant.log
test -s check/ant-out/lib.jar

cat > Ivy253Check.java << 'EOF'
public class Ivy253Check {
    public static void main(String[] args) throws Exception {
        String version = org.apache.ivy.Ivy.getIvyVersion();
        if (!"2.5.3".equals(version)) {
            throw new RuntimeException(version);
        }
        Object handler = org.apache.ivy.util.url.URLHandlerRegistry.getHttp();
        String name = handler.getClass().getName();
        if (!name.equals("org.apache.ivy.util.url.HttpClientHandler")) {
            throw new RuntimeException(name);
        }
        org.apache.ivy.plugins.repository.vfs.VfsRepository repo =
            new org.apache.ivy.plugins.repository.vfs.VfsRepository();
        java.lang.reflect.Method method = repo.getClass().getDeclaredMethod("createVFSManager");
        method.setAccessible(true);
        method.invoke(repo);
        System.out.println("ivy253_ok " + version);
    }
}
EOF
"$JAVA_HOME/bin/javac" --release 8 -proc:none -cp apache-ivy-2.5.3/build/ivy.jar Ivy253Check.java
"$JAVA_HOME/bin/java" -cp "apache-ivy-2.5.3/build/ivy.jar:$deps:." Ivy253Check > check-253.log
cat check-253.log
grep -F -q 'ivy253_ok 2.5.3' check-253.log
"$JAVA_HOME/bin/java" -cp "apache-ivy-2.5.3/build/ivy.jar:$deps" org.apache.ivy.Main -version > check-version-253.log
cat check-version-253.log
grep -F -q 'Apache Ivy 2.5.3' check-version-253.log

%files -f .mfiles
%license LICENSE NOTICE
%doc README.adoc
%{_bindir}/ivy
%{_datadir}/ant/lib/ivy.jar
%config(noreplace) %{_sysconfdir}/ant.d/ivy
