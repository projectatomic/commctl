%global prerelease rc3

Name:           commissaire-client
Version:        0.0.1
Release:        0.2.%{prerelease}%{?dist}
Summary:        CLI for Commissaire
License:        LGPLv2+
URL:            http://github.com/projectatomic/commctl
Source0:        https://github.com/projectatomic/commctl/archive/%{version}%{prerelease}.tar.gz

BuildArch:      noarch

BuildRequires:  python-devel

# For tests
BuildRequires:  python-coverage
BuildRequires:  python-mock
BuildRequires:  python-nose
BuildRequires:  python-flake8

Requires:       python-setuptools
Requires:       py-bcrypt
Requires:       PyYAML

Provides:       commctl

%description
Command line tools for Commissaire.

%prep
%autosetup -n commctl-%{version}%{prerelease}


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
%{_bindir}/commctl
%{python2_sitelib}/*


%changelog
* Mon Jun 06 2016 Matthew Barnes <mbarnes@redhat.com> - 0.0.1-0.2.rc3
- Move pre-release indicator ('rc3') to Release tag for compliance with
  packaging guidelines.
- Add Provides: commctl

* Wed Apr 20 2016 Matthew Barnes <mbarnes@redhat.com> - 0.0.1rc3-1
- Update for RC3.

* Wed Apr 20 2016 Matthew Barnes <mbarnes@redhat.com> - 0.0.1rc2-6
- commissaire-hashpass is now 'commctl create passhash'.

* Mon Apr  4 2016 Steve Milner <smilner@redhat.com> - 0.0.1rc2-5
- commctl and commissaire-hash-pass are now their own package.
