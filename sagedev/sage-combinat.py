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

import re
def import_patch(name, ticket_number=None, append=False, depends=[]):
    """
        sage: %attach sage-combinat.py
        sage: import sagedev
        sage: cd /opt/sage-git
        sage: patch_dir = "/opt/sage/devel/sage/.hg/patches/"
        sage: s = sagedev.SageDev()
        sage: git = s.git
        sage: git.checkout("master")
        sage: destroy_all_branches()
        sage: import_patch("trac9107_nesting_nested_classes.patch")
        sage: import_patch("trac_2023-dynkin_graphs-ts.patch")
        sage: import_patch("trac_14252-KRLS-as.patch")      # Works on second thought
        sage: import_patch("trac_14094-partition_iterator-mh.patch")
        sage: import_patch("trac_14094-partition_iterator-review-ts.patch", append=True)

        sage: import_patch("trac_14145-fix_contains_tableau-ts.patch")
        sage: import_patch("trac_8392-check_permutation-ts.patch")

        sage: import_patch("trac_13871-virtual_cartan_type-ts.patch")
        sage: import_patch("trac_13838-virtual_kleber_alg-ts.patch")  # Does not apply yet (end-of-file whitespace)


        sage: import_patch("trac_13872-RC_bijections-ts.patch")  # Does not apply yet (end-of-file whitespace)

        sage: import_patch("trac9107_nesting_nested_classes.patch")
        sage: import_patch("trac_9107_fix_cross_reference.patch", append=True)

        sage: import_patch("trac_14140-remove_cc_set_partitions-ts.patch")  # Does not apply yet (end-of-file whitespace)

        sage: import_patch("trac_14094-partition_iterator-mh.patch")
        sage: import_patch("trac_14094-partition_iterator-review-ts.patch", append=True)


        sage: import_patch("trac_14248-global_options_case-ts.patch")
        sage: import_patch("trac_14299-gelfand_tsetlin_patterns-ts.patch")
        sage: import_patch("trac_13624-dot2tex-verb_workaround-nt.patch")

        sage: import_patch("trac_10054-parent_gen_words-ts.patch")
        sage: import_patch("trac_14141-knutson_tao_puzzles-fs.patch")
        sage: import_patch("trac_14223-plot-aspect_ratio-nt.patch")
        sage: import_patch("trac_4327-root_system_plot_refactor-nt.patch")  # Does not apply yet (end-of-file whitespace)
        sage: import_patch("trac_14143-alcove-path-al.patch")               # Does not apply yet (end-of-file whitespace)
        sage: import_patch("trac_14192-infinity_crystal-bs.patch")          # Does not apply yet (end-of-file whitespace)
        sage: import_patch("trac_10170-bell_number_improvements-ts.patch")
        sage: import_patch("dynamics-iet-tutorial.patch", )                 # Does not have a ticket number
        sage: import_patch("trac_10193-graded_enumerated_sets-vd_no_more_nt.patch")
        sage: import_patch("trac_10193-review-nb.patch", append=True)
        sage: import_patch("trac_10193-more-vd.patch", append=True)
        sage: import_patch("trac_10194-factories_policy-fh.patch")
        sage: import_patch("trac_12940_affine_permutations-td.patch")        # Does not apply yet (end-of-file whitespace)
        sage: import_patch("trac_12876_category-fix_abstract_class-nt-rel11521.patch")        # Does not apply yet (end-of-file whitespace)
        sage: import_patch("trac_12876_category-fix_abstract_class-nt-rel11521-review-nt.patch")
        sage: import_patch("trac11935_weak_pickling_by_construction_rel11943-nt.patch", depends=[12876])
        sage: import_patch("trac11935_share_on_base_category.patch", append=True)
        sage: import_patch("trac_12894-classcall_setter-nt.patch")

        sage: import_patch("trac_12895-subcategory-methods-nt.patch", depends=[11935])


        sage: import_patch("trac_13580-map_reduce-old-fh.patch")        # Does not apply yet (end-of-file whitespace)
        sage: import_patch("trac_13433-lazy_power_serie_gen_fix-fh.patch")
        sage: import_patch("finite_set_map-isomorphic_cartesian_product-nt.patch")
        sage: import_patch("trac_12848-posets-order_ideal_complement_generators_fix-nt.patch")
        sage: import_patch("trac_12920-is_test_methods-nt.patch")
        sage: import_patch("doc_underscore-fh.patch")
        sage: import_patch("trac_8703-trees-fh.patch")  # Header format
        sage: import_patch("trac_13987_mary_trees-vp.patch", depends=[8703])
        sage: import_patch("trac_11407-list_clone_improve-fh.patch", depends=[8703])
        sage: import_patch("mutator-fh.patch")
        sage: import_patch("trac_9280-graded-algebras-example-fs.patch")
        sage: import_patch("coercion_graph-nt.patch") # No ticket
        sage: import_patch("finiteenumset_random_improve-fh.patch")
        sage: import_patch("trac_12250-ktableaux-as.patch")
        sage: import_patch("trac_9877_words_sturmian_desubstitution-tm.patch") # Header format
        sage: import_patch("missing-doc-includes-nt.patch")
        sage: import_patch("dyck_word_to_binary_tree-fh.patch")
        sage: import_patch("trac_10963-more_functorial_constructions-nt.patch", depends=[12895,9280])
        sage: import_patch("trac_14102-nonsymmetric-macdonald.patch", depends=[4327,14143,10963])
        sage: import_patch("macdonald-refactor-nt.patch")
        sage: import_patch("ncsf-qsym-new-bases-fs.patch")
        sage: import_patch("crystal_isomorphism-ts.patch")
        sage: import_patch("hall_littlewood_yt-ts.patch")
        sage: import_patch("trac_11285-decompose_vecspace-ts.patch")
        sage: import_patch("12630_quivers.patch")
        sage: import_patch("12630_quivers_review-fs.patch")
        sage: import_patch("qpa_interface-fs.patch")
        sage: import_patch("dynamic-fh.patch")
        sage: import_patch("element_compare_consistency-fh.patch")
        sage: import_patch("trees_symmetry_factor-fh.patch")
        sage: import_patch("trac_10950-hash_matrices-nt.patch")
        sage: import_patch("trac_13232-plot_latex-nt.patch")
        sage: import_patch("trac_7980-multiple-realizations-extra_do_not_merge-nt.patch")
        sage: import_patch("kschur-as.patch")
        sage: import_patch("trac_8678-module_morphisms-nt.patch")
        sage: import_patch("trac_13317-species_unique_representation.patch")
        sage: import_patch("trac_10227-species_fixes-mh.patch")
        sage: import_patch("categories-tutorial.patch")
        sage: import_patch("trac_11111-finite_dimensional_modules-nt.patch")
        sage: import_patch("trac_8822-family_constructor-fh.patch")
        sage: import_patch("trac_6484-ranker-improvements-nt.patch")
        sage: import_patch("selector-fh.patch")
        sage: import_patch("trac_11529-rooted_trees-fh.patch")
        sage: import_patch("shape_tree-fc.patch")
        sage: import_patch("shuffle_overlap_generic-fh.patch")
        sage: import_patch("operads-fh.patch")
        sage: import_patch("operads_more-fc.patch")
        sage: import_patch("mupad-interface-improve-fh.patch")
        sage: import_patch("combinat-quickref-jb.patch")
        sage: import_patch("partition_k_boundary_speedup-fh.patch")
        sage: import_patch("partition_leg_length_speedup-fh.patch")
        sage: import_patch("kshape-om.patch")
        sage: import_patch("bintrees_leaf_paths-fh.patch")
        sage: import_patch("trac_11109-stable-grothendieck-polynomials-nt.patch")
        sage: import_patch("add_cache-nt.patch")
        sage: import_patch("games_dao-nt.patch")
        sage: import_patch("finite-subquotients-nt.patch")
        sage: import_patch("finite_set_map_mul-nt.patch")
        sage: import_patch("automatic_monoid-nt.patch")
        sage: import_patch("discrete_function-nt.patch")
        sage: import_patch("discrete_function_exper-fh.patch")
        sage: import_patch("finite_semigroup-nt.patch")
        sage: import_patch("finite_semigroup-subcategory-methods-nt.patch")
        sage: import_patch("digraphs-as-automatons-nt.patch")
        sage: import_patch("category-symmetric_groups-nt.patch")
        sage: import_patch("ndpf_mult_side-fh.patch")
        sage: import_patch("graph-latex-nt.patch")
        sage: import_patch("weyl_characters-nt.patch")
        sage: import_patch("test_len_object-fh.patch")
        sage: import_patch("invariant_ring_permutation_group-nb.patch")
        sage: import_patch("permutation_inverse-vd.patch")
        sage: import_patch("conjugacy_class_iterator-vd.patch")
        sage: import_patch("wang_tile_set-tm.patch")
        sage: import_patch("trac_9439-hyperbolic_geometry-vd.patch")
        sage: import_patch("trac_9557-fundamental_domains-vd.patch")
        sage: import_patch("trac_9806-constellations-vd.patch")
        sage: import_patch("trac_9806-constellations-doc-patch-fc.patch")
        sage: import_patch("permutation_groups_stabilizer_chains-rm.patch")
        sage: import_patch("trac_7983_tableau_fixes-jb.patch")
        sage: import_patch("refactor_sf-jb.patch")
        sage: import_patch("trac_8581_multivariate_schubert_step_1-nb.patch")
        sage: import_patch("trac_6629_abstract_ring_of_multivariate_polynomials_with_several_bases_vp.patch")
        sage: import_patch("trac_12460_polynomial_module_on_sym-nb-vp.patch")
        sage: import_patch("sage-demos-and-tutorials-nt.patch")
        sage: import_patch("graphs_paths_and_cycles_enumeration-abm.patch")
        sage: import_patch("descents_composition_of_empty_permutation_jyt.patch")
        sage: import_patch("exterior_algebra-vd.patch")
        sage: import_patch("nested_lists_jb.patch")
        sage: import_patch("hopf_algebra_of_supercharacters-fs.patch")
        sage: import_patch("permutations_descent_values-fh.patch")
        sage: import_patch("sf_principal_specialization-mr.patch")
        sage: import_patch("trac_9123-schur-algebra-and-gln-characters-ht.patch")
        sage: import_patch("trac_11386_bracelet_class-dr.patch")
        sage: import_patch("trac_11571_catalan_objects-nm.patch")
        sage: import_patch("catalan_quasi_symmetric-fc.patch")
        sage: import_patch("catalan_quasi_symmetric-rebase-cs.patch")
        sage: import_patch("tableaux-combinatorics-am.patch")
        sage: import_patch("cartesian_product_improvements-nt.patch")
        sage: import_patch("extended_affine_weyl_groups_sd40.patch")
        sage: import_patch("affine_iwahori_hecke_algebras.patch")
        sage: import_patch("q_tree_factorial-fc.patch")
        sage: import_patch("trac_12916_completion_by_cuts-fc.patch")
        sage: import_patch("trac_13507_order_polytope-fc.patch")
        sage: import_patch("algebras_over_operads-fc.patch")
        sage: import_patch("shuffle-operads-fc.patch")
        sage: import_patch("trac_Kleshchev-partitions-am.patch")
        sage: import_patch("hgignore_eclipse_project-EliX-jbp.patch")
        sage: import_patch("trac_13935_coercion_of_coproduct_of_Hopf_algebra-EliX-jbp.patch")
        sage: import_patch("trac_13793-some-hopf-algebra-f-w-pqsym-EliX-jbp.patch")
        sage: import_patch("trac_14104--html_display-am.patch")
        sage: import_patch("trac_14103--labelled_matrices-am.patch")
        sage: import_patch("trac_13855_planar_binary_trees_hopf_algebra-EliX-jbp.patch")

    """
    if not ticket_number:
        match = re.match("trac[_-]?(\d\d\d+)",name)
        if not match:
            raise ValueError("Please specify the ticket number")
        ticket = match.groups()[0]
    branch = "t/%s"%ticket
    s = sagedev.SageDev()
    if not append:
        s.git.checkout("master")
        if s.git.branch_exists(branch):
            s.git.branch("-D", branch)
        s.git.create_branch(branch)
        assert s.git.branch_exists(branch)
        s.git.checkout(branch)
        for dependency in depends:
            print dependency
            s.git.merge("t/%s"%dependency)
    s.import_patch(local_file=patch_dir+name, ticketnum=ticket)

def destroy_all_branches():
    s = sagedev.SageDev()
    branches = s.git.local_branches()
    s.git.checkout("master")
    for branch in branches:
        if branch != "master":
            s.git.branch("-D", branch)
