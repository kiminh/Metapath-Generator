import os, sys
import pickle
import random
import networkx as nx
from tqdm import *
from multiprocessing import Pool

DATA_DIR = os.getcwd() + "/data/"
DUMP_DIR = os.getcwd() + "/metapath/"

def meta_path_walk(G, 
                   start, 
                   len_walk,
                   alpha=0.0, 
                   pattern=None):
    """Single Walk Generator

    Generating a single random walk that follows a meta path of `pattern`

    Args:
        rand - an random object to generate random numbers
        start - starting node
        alpha - probability of restarts
        pattern - (string) the pattern according to which to generate walks
        walk_len - (int) the length of the generated walk

    Return:
        walk - the single walk generated

    """
    rand = random.Random()
    # Checking pattern is correctly initialized
    if not pattern:
        sys.exit("Pattern is not specified when generating meta-path walk")

    pat_ind = 1
    walk = [start]
    cur_node = start

    # Generating meta-paths
    while len(walk) <= len_walk or pat_ind != len(pattern):

        # Updating the pattern index
        pat_ind = pat_ind if pat_ind != len(pattern) else 1

        # Decide whether to restart
        if rand.random() >= alpha:
            # Find all possible next neighbors
                # possible_next_node = [neighbor
                #                       for neighbor in G.neighbors(cur_node)
                #                       if type_of(neighbor) == pattern[pat_ind]]
            possible_next_node = list(G[cur_node][pattern[pat_ind]])
            # Random choose next node
            try:
                next_node = rand.choice(possible_next_node)
            except:
                return " ".join([str(x) for x in walk])
        else:
            next_node = walk[0]

        walk.append(next_node)
        cur_node = next_node
        pat_ind += 1

    return " ".join([str(x) for x in walk])

def main(dataset, len_walk, cvg, use_full, multiproc):

    # =============
    # Load Metapath
    # =============
    with open(DATA_DIR + 
              "{}.metapath".format(dataset), "r") as fin:
        metapaths = [x.strip() for x in fin.readlines()]

    # ===============
    # Load Node Types 
    # ===============

    with open(DATA_DIR + "{}.type".format(dataset), "rb") as fin:
        node_types = pickle.load(fin)
    all_types = list(set(node_types))
    print("\t- [Loading node type: Done!]")

    # ============================
    # Load Edges, Build Network
    # ============================

    type_nbrs = {}
    type_nodes = dict(zip(all_types, [set() for _ in range(len(all_types))]))

    dataset_suffix = "" if use_full else ".lp.train" 
    with open(DATA_DIR + "{}.edges{}".format(dataset, dataset_suffix), "r") as fin:
        for line in fin.readlines():
            id1, id2 = [int(x) for x in line.strip().split("\t")]
            type1 = node_types[id1]
            type2 = node_types[id2]
            if id1 not in type_nbrs:
                type_nbrs[id1] = dict(zip(all_types, [set() for _ in range(len(all_types))]))
            if id2 not in type_nbrs:
                type_nbrs[id2] = dict(zip(all_types, [set() for _ in range(len(all_types))]))
            
            type_nbrs[id1][type2].add(id2)
            type_nbrs[id2][type1].add(id1)
            type_nodes[type1].add(id1)
            type_nodes[type2].add(id2)
        
        # print(type_nbrs)
        
    print("\t- [Building graph: Done!]")
    
    # ====================
    # Generate Random Walk
    # ====================

    print("\t- Generating walks ...")

    rand = random.Random(2019)
    walks = []

    for mp in metapaths:
        print("\t\t - now by MP-{}".format(mp))
        init_node_type = mp[0]
        # init_node_list = get_typed_nodes(G, init_node_type)
        init_node_list = list(type_nodes[init_node_type])

        async_results = []

        if multiproc > 1:
            cvg_per_process = cvg // multiproc
            pool = Pool(processes=multiproc)

            for i in range(multiproc):
                res = pool.apply_async(worker, 
                                       args=(type_nbrs, 
                                             init_node_list, 
                                             cvg_per_process,
                                             len_walk,
                                             mp))
                async_results.append(res)

            pool.close()
            pool.join()

            for r in async_results:
                walks += r.get()

        else:
            for _ in tqdm(range(cvg)):  # Iterate the node set for cnt times
                rand.shuffle(init_node_list)
                for init_node in init_node_list:
                    walks.append(
                            meta_path_walk(
                                type_nbrs, 
                                start=init_node, 
                                len_walk=len_walk, 
                                pattern=mp))
                    # print(walks)
    print("\t\tNumber of walks generated :", end=" ")
    print(len(walks))

    print("\t- [Generate walks: Done!]")
    
    # =======================
    # Dumping generated walks
    # =======================

    if not os.path.isdir(DUMP_DIR):
        os.mkdir(DUMP_DIR)
    
    with open(DUMP_DIR + 
              "{}.walks{}".format(dataset, dataset_suffix), "w") as fout:
        for walk in walks:
            fout.write(walk + "\n")
    
    print("\t- [Dumping walks: Done!]")
    print("Process Succeeded!")

def worker(G, init_node_list, cvg, len_walk, metapath):
    rand = random.Random(2019)
    per_walks = []
    for _ in range(cvg):  # Iterate the node set for cnt times
        rand.shuffle(init_node_list)
        for init_node in init_node_list:
            per_walks.append(
                    meta_path_walk(
                        G, 
                        start=init_node, 
                        len_walk=len_walk, 
                        pattern=metapath))
            # print(per_walks[-1])
    return per_walks

if __name__ == "__main__":
    if len(sys.argv) != 1 + 5:  # TODO
        print("Invalid Parameters!")
        print("Usage:\n",
              "\tpython {} [dataset]".format(sys.argv[0]),
              "[full_graph] [length_of_walk] [coverage] [multiprocessing]")
        sys.exit(1)

    dataset = sys.argv[1]
    use_full = (int(sys.argv[2]) == 1)
    len_walk = int(sys.argv[3])
    cvg = int(sys.argv[4])
    multiproc = int(sys.argv[5])

    print("Metapath Generation:\n",
          "\tProcessing dataset: {}\n".format(dataset),
          "\tUsing full graph: {}\n".format("True" if use_full else "False"),
          "\tLength of Walk: {}, Coverage: {}".format(len_walk, cvg))

    main(dataset,
         len_walk,
         cvg,
         use_full,
         multiproc)    

