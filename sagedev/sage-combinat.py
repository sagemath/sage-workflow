import re
import sagedev

"""
    sage: import sagedev
    sage: %attach sage-combinat.py
    sage: cd /opt/sage-git
    sage: patch_dir = "/opt/sage/devel/sage/.hg/patches/"
    sage: s = sagedev.SageDev()
    sage: git = s.git
    sage: git.checkout("master")

    sage: git.branch("-D", "t/9107")
    Deleted branch t/9107 (was 031ee52).

    sage: s.import_patch(local_file=patch_dir+"trac9107_nesting_nested_classes.patch", ticketnum=9107)
    sage: s.import_patch(local_file=patch_dir+"trac_9107_fix_cross_reference.patch", ticketnum=9107)

    sage: git.checkout("master")

# Breaks due to the removal of new lines

    sage: git.branch("-D", "t/14140")
    sage: s.import_patch(local_file=patch_dir+"trac_14140-remove_cc_set_partitions-ts.patch", ticketnum=14140)

    sage: git.checkout("master")
    sage: s.import_patch(local_file=patch_dir+"trac_14248-global_options_case-ts.patch", ticketnum=14248)

    sage: git.checkout("master")
    sage: s.import_patch(local_file=patch_dir+"trac_14299-gelfand_tsetlin_patterns-ts.patch", ticketnum=14299)

    sage: git.checkout("master")
    sage: s.import_patch(local_file=patch_dir+"trac_13624-dot2tex-verb_workaround-nt.patch", ticketnum=13624)

"""

patch_dir = "/opt/sage/devel/sage/.hg/patches/"

def import_patch(name, ticket_number=None, append=False, depends=[]):
    """
    EXAMPLES::

        sage: %attach sage-combinat.py
        sage: import sagedev
        sage: cd /opt/sage-git
        sage: destroy_all_branches()
        sage: import_patch("trac9107_nesting_nested_classes.patch")
        sage: import_patch("trac_12876_category-fix_abstract_class-nt-rel11521.patch")
        sage: import_patch("trac_12876_category-fix_abstract_class-nt-rel11521-review-nt.patch", append=True)
        sage: import_patch("trac11935_weak_pickling_by_construction_rel11943-nt.patch", depends=[12876])
        sage: import_patch("trac11935_share_on_base_category.patch", append=True)
        sage: import_patch("trac_12894-classcall_setter-nt.patch")

    """
    print "== Importing patch %s "%name + "="*max(60-len(name), 0)
    if not ticket_number:
        match = re.match(".*?(\d\d\d\d+)",name)
        if not match:
            raise ValueError("Please specify the ticket number")
        ticket = match.groups()[0]
    branch = "t/%s"%ticket
    s = sagedev.SageDev()
    if not append:
        s.git.checkout("master")
        if s.git.branch_exists(branch):
            s.git.branch("-D", branch)
        #s.git.create_branch(branch)
        s.git.create_branch(branch, remote_branch=False)
        assert s.git.branch_exists(branch)
        s.git.checkout(branch)
        for dependency in depends:
            print dependency
            s.git.merge("t/%s"%dependency)
    s.import_patch(local_file=patch_dir+name)

def destroy_all_branches():
    s = sagedev.SageDev()
    branches = s.git.local_branches()
    s.git.checkout("master")
    for branch in branches:
        if branch != "master":
            s.git.branch("-D", branch)

def git_reset():
    s = sagedev.SageDev()
    branches = s.git.local_branches()
    s.git.checkout("master")
    s.git.clean("-f", "-d")

def import_sage_combinat():
    """
    EXAMPLES::

        sage: %attach sage-combinat.py
        sage: cd /opt/sage-git
        sage: import_sage_combinat()
    """
    git = sagedev.SageDev().git
    destroy_all_branches()
    git.clean("-f")
    import_patch("trac9107_nesting_nested_classes.patch")
    import_patch("trac_2023-dynkin_graphs-ts.patch")
    # Applies on second thought
    import_patch("trac_14252-KRLS-as.patch", )
    import_patch("trac_14094-partition_iterator-mh.patch")
    import_patch("trac_14094-partition_iterator-review-ts.patch", append=True)

    import_patch("trac_14145-fix_contains_tableau-ts.patch")
    import_patch("trac_8392-check_permutation-ts.patch")

    import_patch("trac_13871-virtual_cartan_type-ts.patch")
    import_patch("trac_13838-virtual_kleber_alg-ts.patch")

    import_patch("trac_13872-RC_bijections-ts.patch", depends=[13838])

    import_patch("trac9107_nesting_nested_classes.patch")
    import_patch("trac_9107_fix_cross_reference.patch", append=True)

    import_patch("trac_14140-remove_cc_set_partitions-ts.patch")

    import_patch("trac_14094-partition_iterator-mh.patch")
    import_patch("trac_14094-partition_iterator-review-ts.patch", append=True)


    import_patch("trac_14248-global_options_case-ts.patch")
    import_patch("trac_14299-gelfand_tsetlin_patterns-ts.patch")
    import_patch("trac_13624-dot2tex-verb_workaround-nt.patch")

    import_patch("trac_10054-parent_gen_words-ts.patch")
    import_patch("trac_14141-knutson_tao_puzzles-fs.patch")
    import_patch("trac_14223-plot-aspect_ratio-nt.patch")
    import_patch("trac_4327-root_system_plot_refactor-nt.patch")
    import_patch("trac_14143-alcove-path-al.patch", depends=[14252])
    import_patch("trac_14192-infinity_crystal-bs.patch", depends=[14252,14143]) # Trivial textual dependencies
    import_patch("trac_10170-bell_number_improvements-ts.patch")
    #import_patch("dynamics-iet-tutorial.patch", )                 # Does not have a ticket number
    import_patch("trac_10193-graded_enumerated_sets-vd_no_more_nt.patch")
    import_patch("trac_10193-review-nb.patch", append=True)
    import_patch("trac_10193-more-vd.patch", append=True)
    import_patch("trac_10194-factories_policy-fh.patch")
    import_patch("trac_12940_affine_permutations-td.patch", depends=[8392]) # Trivial dependency in sage.combinat.all
    import_patch("trac_12876_category-fix_abstract_class-nt-rel11521.patch")        # Does not apply yet (end-of-file whitespace)
    import_patch("trac_12876_category-fix_abstract_class-nt-rel11521-review-nt.patch", append=True)
    import_patch("trac11935_weak_pickling_by_construction_rel11943-nt.patch", depends=[12876])
    import_patch("trac11935_share_on_base_category.patch", append=True)
    import_patch("trac_12894-classcall_setter-nt.patch")

    import_patch("trac_12895-subcategory-methods-nt.patch", depends=[11935,12894])

    import_patch("trac_13580-map_reduce-old-fh.patch")        # Does not apply yet (end-of-file whitespace)
    import_patch("trac_13433-lazy_power_serie_gen_fix-fh.patch")
    #import_patch("finite_set_map-isomorphic_cartesian_product-nt.patch")
    import_patch("trac_12848-posets-order_ideal_complement_generators_fix-nt.patch")
    #import_patch("trac_12920-is_test_methods-nt.patch") # Needs rebase upon #14284
    #import_patch("doc_underscore-fh.patch")
    import_patch("trac_8703-trees-fh.patch", depends=[8392])     # in permutations.py
    import_patch("trac_13987_mary_trees-vp.patch", depends=[8703])
    import_patch("trac_11407-list_clone_improve-fh.patch", depends=[8703])
    #import_patch("mutator-fh.patch")
    import_patch("trac_9280-graded-algebras-example-fs.patch")
    #import_patch("coercion_graph-nt.patch") # No ticket
    #import_patch("finiteenumset_random_improve-fh.patch")
    import_patch("trac_12250-ktableaux-as.patch")
    #import_patch("missing-doc-includes-nt.patch")
    #import_patch("dyck_word_to_binary_tree-fh.patch")
    import_patch("trac_10963-more_functorial_constructions-nt.patch", depends=[10193,12895,9280])
    import_patch("trac_14102-nonsymmetric-macdonald.patch", depends=[4327,14143,10963])
    #import_patch("ncsf-qsym-new-bases-fs.patch")
    #import_patch("crystal_isomorphism-ts.patch")
    #import_patch("hall_littlewood_yt-ts.patch")
    import_patch("trac_11285-decompose_vecspace-ts.patch")
    import_patch("12630_quivers.patch")
    import_patch("12630_quivers_review-fs.patch")
    #import_patch("qpa_interface-fs.patch")
    #import_patch("dynamic-fh.patch")
    #import_patch("element_compare_consistency-fh.patch")
    #import_patch("trees_symmetry_factor-fh.patch")
    import_patch("trac_10950-hash_matrices-nt.patch")
    import_patch("trac_13232-plot_latex-nt.patch")
    #import_patch("kschur-as.patch")
    import_patch("trac_8678-module_morphisms-nt.patch", depends=[10963])
    import_patch("trac_13317-species_unique_representation.patch")
    import_patch("trac_10227-species_fixes-mh.patch", depends=[13317])
    #import_patch("categories-tutorial.patch")
    import_patch("trac_11111-finite_dimensional_modules-nt.patch", depends=[10963,8678]) # still causing problem
    import_patch("trac_8822-family_constructor-fh.patch")
    import_patch("trac_6484-ranker-improvements-nt.patch")
    #import_patch("selector-fh.patch")
    import_patch("trac_11529-rooted_trees-fh.patch", depends=[8703,13987]) # causing problem
    #import_patch("shape_tree-fc.patch")
    #import_patch("shuffle_overlap_generic-fh.patch")
    #import_patch("operads-fh.patch")
    #import_patch("operads_more-fc.patch")
    #import_patch("mupad-interface-improve-fh.patch")
    #import_patch("combinat-quickref-jb.patch")
    #import_patch("partition_k_boundary_speedup-fh.patch")
    #import_patch("partition_leg_length_speedup-fh.patch")
    #import_patch("kshape-om.patch")
    #import_patch("bintrees_leaf_paths-fh.patch")
    import_patch("trac_11109-stable-grothendieck-polynomials-nt.patch", depends=[10963]) # really depends on it?
    #import_patch("add_cache-nt.patch")
    #import_patch("games_dao-nt.patch")
    #import_patch("finite-subquotients-nt.patch")
    #import_patch("finite_set_map_mul-nt.patch")
    #import_patch("automatic_monoid-nt.patch")
    #import_patch("discrete_function-nt.patch")
    #import_patch("discrete_function_exper-fh.patch")
    #import_patch("finite_semigroup-nt.patch")
    #import_patch("finite_semigroup-subcategory-methods-nt.patch")
    #import_patch("digraphs-as-automatons-nt.patch")
    #import_patch("category-symmetric_groups-nt.patch")
    #import_patch("ndpf_mult_side-fh.patch")
    #import_patch("graph-latex-nt.patch")
    #import_patch("weyl_characters-nt.patch")
    #import_patch("test_len_object-fh.patch")
    #import_patch("invariant_ring_permutation_group-nb.patch")
    #import_patch("permutation_inverse-vd.patch")
    #import_patch("conjugacy_class_iterator-vd.patch")
    #import_patch("wang_tile_set-tm.patch")
    import_patch("trac_9439-hyperbolic_geometry-vd.patch")
    import_patch("trac_9557-fundamental_domains-vd.patch", depends=[9439])
    import_patch("trac_9806-constellations-vd.patch", depends=[9557])
    import_patch("trac_9806-constellations-doc-patch-fc.patch", append=True)
    #import_patch("permutation_groups_stabilizer_chains-rm.patch")
    import_patch("trac_7983_tableau_fixes-jb.patch")
    #import_patch("refactor_sf-jb.patch")
    #import_patch("trac_8581_multivariate_schubert_step_1-nb.patch")  # depends trivially on invariant_ring_permutation_group-nb.patch
    #import_patch("trac_6629_abstract_ring_of_multivariate_polynomials_with_several_bases_vp.patch")
    #import_patch("trac_12460_polynomial_module_on_sym-nb-vp.patch")
    #import_patch("sage-demos-and-tutorials-nt.patch")
    #import_patch("graphs_paths_and_cycles_enumeration-abm.patch")
    #import_patch("descents_composition_of_empty_permutation_jyt.patch")
    #import_patch("exterior_algebra-vd.patch")
    #import_patch("nested_lists_jb.patch")
    #import_patch("trac_7980-multiple-realizations-extra_do_not_merge-nt.patch")
    #import_patch("hopf_algebra_of_supercharacters-fs.patch")
    #import_patch("permutations_descent_values-fh.patch")
    #import_patch("sf_principal_specialization-mr.patch")
    import_patch("trac_9123-schur-algebra-and-gln-characters-ht.patch")
    import_patch("trac_11386_bracelet_class-dr.patch")
    import_patch("trac_11571_catalan_objects-nm.patch")
    #import_patch("catalan_quasi_symmetric-fc.patch")
    #import_patch("catalan_quasi_symmetric-rebase-cs.patch")
    #import_patch("tableaux-combinatorics-am.patch")
    #import_patch("cartesian_product_improvements-nt.patch")
    #import_patch("extended_affine_weyl_groups_sd40.patch")
    #import_patch("affine_iwahori_hecke_algebras.patch")
    #import_patch("q_tree_factorial-fc.patch")
    import_patch("trac_12916_completion_by_cuts-fc.patch")
    #import_patch("algebras_over_operads-fc.patch")
    #import_patch("shuffle-operads-fc.patch")
    #import_patch("trac_Kleshchev-partitions-am.patch")
    #import_patch("hgignore_eclipse_project-EliX-jbp.patch")
    import_patch("trac_13935_coercion_of_coproduct_of_Hopf_algebra-EliX-jbp.patch")
    import_patch("trac_13793-some-hopf-algebra-f-w-pqsym-EliX-jbp.patch", depends=[11571,13935]) # Trivial dependency upon #11571 in setup.py Trivial dependency on invariant_ring_permutation_group-nb.patch in doc/en/reference/combinat/index.rst
    import_patch("trac_14104--html_display-am.patch")
    import_patch("trac_14103--labelled_matrices-am.patch")
    import_patch("trac_13855_planar_binary_trees_hopf_algebra-EliX-jbp.patch", depends=[8703,13793]) # and q_tree_factorial-fc.patch and trees_symmetry_factor-fh.patch
