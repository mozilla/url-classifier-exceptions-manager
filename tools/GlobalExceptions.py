def postprocess_fix_domains(fix_domains):
    # TODO: This is a hardcoded hack
    ret = set()

    for fix_domain in fix_domains:
        if ".userapi.com" in fix_domain or fix_domain == "userapi.com":
            ret.add("*.userapi.com")
        elif ".vk.com" in fix_domain or fix_domain == "vk.com":
            ret.add("*.vk.com")
        else:
            ret.add(fix_domain)

    return list(ret)

class GlobalExceptions:
    def __init__(self, global_exceptions_file):
        with open(global_exceptions_file, "r") as fd:
            self.global_exceptions = [x.replace("*.", "", 1).strip() if x.startswith("*.") else x.strip() for x in fd.readlines()]

    def filter_global_exceptions(self, fix_domains):
        fix_domains = fix_domains.split(",")
        fix_domains = postprocess_fix_domains(fix_domains)
        fix_domains.sort()

        matched_one = False
        matched_all = True

        necessary_fix_domains = []

        for fix_domain in fix_domains:
            found_exception_match = False
            for exc in self.global_exceptions:
                if exc in fix_domain:
                    found_exception_match = True
                    break

            if not found_exception_match:
                necessary_fix_domains.append(fix_domain)

        return necessary_fix_domains
