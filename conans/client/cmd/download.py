import os
from conans.client.output import ScopedOutput
from conans.client.source import complete_recipe_sources
from conans.model.ref import ConanFileReference, PackageReference
from conans.client.file_copier import FileCopier
from conans.client.remote_manager import unzip_and_get_files
from conans.util.files import touch_folder, rmdir
from conans.paths import  PACKAGE_TGZ_NAME

def download(ref, package_ids, remote, recipe, remote_manager,
             cache, out, recorder, loader, hook_manager, remotes):

    assert(isinstance(ref, ConanFileReference))
    output = ScopedOutput(str(ref), out)

    # Copying package_ids because I don't know if there are used in other modules
    pkgs_ids = list(package_ids)
    for package_id in pkgs_ids:
        pref = PackageReference(ref, package_id)
        cached = _copy_cached(pref, cache, output)
        if (cached):
            pkgs_ids.remove(package_id)

    hook_manager.execute("pre_download", reference=ref, remote=remote)

    if package_ids and not len(pkgs_ids):
        output.info("All packages copy from cache")
        return

    ref = remote_manager.get_recipe(ref, remote)
    with cache.package_layout(ref).update_metadata() as metadata:
        metadata.recipe.remote = remote.name

    conan_file_path = cache.conanfile(ref)
    conanfile = loader.load_class(conan_file_path)

    if not recipe:  # Not only the recipe
        # Download the sources too, don't be lazy
        complete_recipe_sources(remote_manager, cache, conanfile, ref, remotes)

        if not package_ids:  # User didn't specify a specific package binary
            output.info("Getting the complete package list from '%s'..." % ref.full_repr())
            packages_props = remote_manager.search_packages(remote, ref, None)
            pkgs_ids = list(packages_props.keys())
            if not package_ids:
                output.warn("No remote binary packages found in remote")

        _download_binaries(conanfile, ref, pkgs_ids, cache, remote_manager,
                           remote, output, recorder)
    hook_manager.execute("post_download", conanfile_path=conan_file_path, reference=ref,
                         remote=remote)


def _download_binaries(conanfile, ref, package_ids, cache, remote_manager, remote, output,
                       recorder):
    short_paths = conanfile.short_paths

    for package_id in package_ids:
        pref = PackageReference(ref, package_id)
        package_folder = cache.package(pref, short_paths=short_paths)
        output.info("Downloading %s" % str(pref))
        remote_manager.get_package(pref, package_folder, remote, output, recorder)

def _copy_cached(pref, cache, output):
        package_folder = cache.package(pref)
        #FIXME 'data' and 'cached' from configuration file
        cache_folder = package_folder.replace('data', 'cached')
        if os.path.exists(cache_folder):
            rmdir(package_folder)
            output.info("Getting packages from cache")
            zipped_files={}
            copier = FileCopier([cache_folder], package_folder)
            files = copier("*", links=True)
            for file_path in files:
                file_name = os.path.basename(file_path)
                zipped_files[file_name]=file_path

            unzip_and_get_files(zipped_files, package_folder, PACKAGE_TGZ_NAME, output)
            touch_folder(package_folder)
            return True
        else:
            return False
