Name:           commissaire-cli
Version:        0.0.1rc2
Release:        5%{?dist}
Summary:        CLI for Commissaire
License:        LGPLv2+
URL:            http://github.com/projectatomic/commctl
Source0:        https://github.com/projectatomic/%{name}/archive/%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python-devel

# For tests
BuildRequires:  python-coverage
BuildRequires:  python-mock
BuildRequires:  python-nose
BuildRequires:  python-flake8

Requires:  python-setuptools
Requires:  py-bcrypt

%description
Command line tools for Commissaire.

%prep
%autosetup -n commctl-%{version}


%build
%py2_build

%install
%py2_install

%check
# XXX: Issue with the coverage module.
#%{__python2} setup.py nosetests


%files
%license COPYING
%doc README.md
%doc CONTRIBUTORS
%doc MAINTAINERS
%{_bindir}/commissaire-hashpass
%{_bindir}/commctl
%{python2_sitelib}/*


%changelog
* Mon Apr  4 2016 Steve Milner <smilner@redhat.com> - 0.0.1rc2-5
* commctl and commissaire-hash-pass are now their own package.
