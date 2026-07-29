package course.taica.hw3;

import org.apache.jena.query.Query;
import org.apache.jena.query.QueryExecution;
import org.apache.jena.query.QueryExecutionFactory;
import org.apache.jena.query.QueryFactory;
import org.apache.jena.query.QuerySolution;
import org.apache.jena.query.ResultSetFactory;
import org.apache.jena.query.ResultSetFormatter;
import org.apache.jena.query.ResultSetRewindable;
import org.apache.jena.rdf.model.InfModel;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.Statement;
import org.apache.jena.rdf.model.StmtIterator;
import org.apache.jena.reasoner.Derivation;
import org.apache.jena.reasoner.Reasoner;
import org.apache.jena.reasoner.ReasonerRegistry;
import org.apache.jena.reasoner.ValidityReport;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.riot.RDFFormat;
import org.apache.jena.vocabulary.RDF;
import org.apache.jena.vocabulary.ReasonerVocabulary;

import java.io.File;
import java.io.FileOutputStream;
import java.io.PrintWriter;
import java.util.Iterator;

/**
 * TAICA HW3 — Task 4 semantic engine (TA-provided, no student TODO here).
 *
 * Pipeline position: runs BEFORE the triple store is loaded.
 *   1. Load the base ontology + any number of data graphs (student's UR5
 *      graph, TA's UR10 graph, ...).
 *   2. Bind Jena's OWL rule reasoner and materialize the deductions —
 *      this is where hw3:SolvedIKComputation memberships are derived.
 *   3. Export asserted + inferred triples to a Turtle file, which
 *      run_task4.sh then bulk-loads into the TDB2 triple store.
 *   4. (optional) Run one SPARQL query directly and print machine-parsable
 *      "RESULT|..." lines — handy for debugging without the triple store.
 *
 * Usage:
 *   java course.taica.hw3.SemanticReasoner \
 *        &lt;inferred_out.ttl&gt; &lt;query.rq | - &gt; &lt;input1.ttl&gt; [input2.ttl ...]
 *
 *   Pass "-" as the query argument to skip query execution (Task 4 default:
 *   queries are instead answered by the TDB2 triple store via tdb2.tdbquery).
 */
public final class SemanticReasoner {

    private SemanticReasoner() { }

    public static void main(String[] args) throws Exception {
        if (args.length < 3) {
            System.err.println(
                "usage: SemanticReasoner <inferred_out.ttl> <query.rq|-> <in1.ttl> [in2.ttl ...]");
            System.exit(2);
        }
        final String outPath = args[0];
        final String queryPath = args[1];

        // ---- 1. Load base ontology + all data graphs ----
        Model data = ModelFactory.createDefaultModel();
        for (int i = 2; i < args.length; i++) {
            Model m = RDFDataMgr.loadModel(args[i]);
            data.add(m);
            data.setNsPrefixes(m);
            System.out.println("[LOAD] " + m.size() + " triples from " + args[i]);
        }

        // ---- 2. Bind the OWL reasoner ----
        // Jena ships a rule-based OWL reasoner (HermiT / Pellet are NOT part
        // of Jena). The intersectionOf + hasValue patterns used by the HW3
        // ontology are fully supported.
        Reasoner reasoner = ReasonerRegistry.getOWLReasoner();
        // Record HOW each fact is derived (rule + premises), so the
        // derivation traces of the evaluation classes can be exported.
        reasoner.setParameter(ReasonerVocabulary.PROPderivationLogging, Boolean.TRUE);
        InfModel infModel = ModelFactory.createInfModel(reasoner, data);

        ValidityReport validity = infModel.validate();
        if (validity.isValid()) {
            System.out.println("[REASON] ontology + data are consistent");
        } else {
            System.out.println("[REASON] CONSISTENCY VIOLATIONS:");
            for (Iterator<ValidityReport.Report> it = validity.getReports(); it.hasNext(); ) {
                System.out.println("  - " + it.next());
            }
        }

        // ---- 3. Export asserted + inferred triples ----
        // Note: copy the FULL InfModel closure, not just getDeductionsModel().
        // Jena's OWL reasoner derives class memberships for hasValue /
        // intersectionOf patterns via BACKWARD rules, which never appear in
        // the forward deductions model — enumerating the InfModel forces
        // those derivations to materialize.
        Model export = ModelFactory.createDefaultModel();
        export.add(infModel);
        export.setNsPrefixes(data);
        try (FileOutputStream out = new FileOutputStream(outPath)) {
            RDFDataMgr.write(out, export, RDFFormat.TURTLE_PRETTY);
        }
        System.out.println("[EXPORT] inferred graph (" + export.size()
                + " triples) written to " + outPath);

        // ---- 3b. Export derivation traces of the evaluation classes ----
        // For every reasoner-derived membership fact, dump WHICH rule fired
        // and WHICH asserted premises it used — the "proof" of the inference.
        final String HW3 = "http://taica.course/hw3/ontology#";
        final String[] evalClasses = {
            HW3 + "PassedFKComputation",
            HW3 + "SolvedIKComputation",
            HW3 + "SuccessfulEpisode",
        };
        File derivFile = new File(
                new File(outPath).getAbsoluteFile().getParentFile(),
                "derivations.txt");
        int derived = 0;
        try (PrintWriter pw = new PrintWriter(derivFile, "UTF-8")) {
            for (String cls : evalClasses) {
                Resource c = infModel.getResource(cls);
                StmtIterator si = infModel.listStatements(null, RDF.type, c);
                while (si.hasNext()) {
                    Statement s = si.next();
                    pw.println("================================================================");
                    pw.println("DERIVED FACT : " + s.getSubject().getLocalName()
                            + "  rdf:type  hw3:" + c.getLocalName());
                    pw.println("----------------------------------------------------------------");
                    Iterator<Derivation> dit = infModel.getDerivation(s);
                    int paths = 0;
                    while (dit.hasNext()) {
                        Derivation d = dit.next();
                        if (paths == 0) {
                            d.printTrace(pw, true);   // first proof chain only
                        }
                        paths++;
                    }
                    if (paths == 0) {
                        pw.println("(no forward-rule trace recorded — this fact was"
                                + " produced by the backward-chaining engine)");
                    } else if (paths > 1) {
                        pw.println("(" + (paths - 1)
                                + " additional equivalent derivation path(s) omitted)");
                    }
                    pw.println();
                    derived++;
                }
            }
        }
        System.out.println("[DERIVE] " + derived
                + " derivation traces written to " + derivFile);

        // ---- 4. Optional direct SPARQL query (semantic-gate mode) ----
        if (!"-".equals(queryPath)) {
            Query query = QueryFactory.read(queryPath);
            System.out.println("[SPARQL] executing " + queryPath);
            try (QueryExecution qe = QueryExecutionFactory.create(query, infModel)) {
                ResultSetRewindable results = ResultSetFactory.copyResults(qe.execSelect());
                ResultSetFormatter.out(System.out, results, query);
                results.reset();

                int count = 0;
                while (results.hasNext()) {
                    QuerySolution s = results.next();
                    String obj = s.contains("obj") ? s.getResource("obj").getURI() : "";
                    String label = s.contains("label") ? s.getLiteral("label").getString() : "";
                    String status = s.contains("status") ? s.getLiteral("status").getString() : "";
                    String err = s.contains("err") ? s.getLiteral("err").getLexicalForm() : "";
                    System.out.println("RESULT|" + obj + "|" + label + "|" + status + "|" + err);
                    count++;
                }
                System.out.println("[SPARQL] " + count + " result row(s)");
            }
        }
    }
}
