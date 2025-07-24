import pandas as pd
def main(file_name="./data/icd10cm_codes_2022.txt"):

    with open(file_name) as f:

        code_list = []
        for line in f:
            code = line[0:6].strip()
            description=line[7:].strip()
            code_list += [[code,description]]

    df = pd.DataFrame(code_list, columns=["Code", "Description"])

    df.to_csv("./data/icd10cm_codes_2022.csv", index=False)

    print(df.head(5))

if __name__ == "__main__":
    main()